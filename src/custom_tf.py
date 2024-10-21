from sympy import N
import torch, os
import monai.transforms as mtf
import nibabel as nib
import numpy as np
from monai.data.meta_tensor import MetaTensor

class CTImageProcessor:
    def __init__(self, case_path, ct_name='ct', mask_name='liver', mask_path=None):
        """
        Initialize the CTImageProcessor class, loading the CT image and retaining the affine and header information.
        
        Parameters:
        - ct_file: Path to the CT image NIfTI file
        """
        self.case_path = case_path
        self.ct_name = ct_name
        self.mask_name = mask_name
        
        # Load the CT image
        try:
            print(case_path)
            self.ct_nifti = nib.load(os.path.join(case_path, ct_name+".nii.gz"))
        except:
            case = case_path.split("/")[-1]
            self.ct_nifti = nib.load(os.path.join("/mnt/T9/AbdomenAtlasPro", case, ct_name+".nii.gz"))
        self.affine = self.ct_nifti.affine
        self.header = self.ct_nifti.header
        
        # Load the mask
        # If mask_path is not provided, assume the mask is in the same directory as the CT image
        if not mask_path: # 
            case_path = mask_path
        if mask_name == "kidneys":
            # load kidney_left and kidney_right masks and merge them into one mask kidneys
            self.mask1 = nib.load(os.path.join(case_path, "segmentations", "kidney_left.nii.gz"))
            self.mask2 = nib.load(os.path.join(case_path, "segmentations", "kidney_right.nii.gz"))
            self.mask = nib.Nifti1Image(
                np.maximum(self.mask1.get_fdata(), self.mask2.get_fdata()), 
                affine=self.mask1.affine, 
                header=self.mask1.header
            )
            del self.mask1, self.mask2
        else:
            self.mask = nib.load(os.path.join(case_path, "segmentations", mask_name+".nii.gz")) 
 
        # Convert the CT image and mask to MetaTensor objects
        self.ct_image = MetaTensor(
            self.ct_nifti.get_fdata().transpose(2, 0, 1)[np.newaxis, ...], 
            affine=self.affine,
            header=self.header
        )
        self.ct_mask = MetaTensor(
            self.mask.get_fdata().transpose(2, 0, 1)[np.newaxis, ...], 
            affine=self.affine,
            header=self.header
        )
        
        self.transformed = None
        self.apply_transforms()
        
        self.ctmin_image = None
        self.get_ctmin()
        self.ctmin_transformed = None
        ctmin_pair = {"image": self.ctmin_image, "seg": self.ct_mask}
        self.ctmin_transformed = self.transforms(ctmin_pair)
        
        # del self.ct_nifti, self.mask  # Clear up memory
        self.mask_present = False if np.all(self.mask.get_fdata() == 0) else True

    def get_ctmin(self):
        ctmin_np = self.ct_nifti.get_fdata().copy()
        ctmin_np[self.mask.get_fdata()==1] = ctmin_np.min()
        self.ctmin_image = MetaTensor(
            ctmin_np.transpose(2, 0, 1)[np.newaxis, ...], 
            affine=self.affine,
            header=self.header
        )
        del ctmin_np
        
    def apply_transforms(self):
        """
        Apply specified transformations to the CT image and return the transformed image and transform object.
        
        Returns:
        - transformed_image: Transformed image
        - transforms: Transformation object for inverse transformation
        """
        # Define the transformations
        self.transforms = mtf.Compose([
            mtf.ScaleIntensityRangePercentilesd(
                keys=["image"], lower=0.5, upper=99.5, b_max=1.0, b_min=0.0, clip=True
            ),
            mtf.CropForegroundd(
                keys=["image", "seg"], 
                source_key="image"
            ),
            mtf.Resized(
                keys=["image", "seg"], 
                spatial_size=[32, 256, 256], 
                mode=['trilinear', 'nearest']
            ),
        ])

        # Apply transformations
        pair = {"image": self.ct_image, "seg": self.ct_mask}
        self.transformed = self.transforms(pair)

    def invert_mask(self, predicted_mask, output_path, get_noninver=False):
        """
        Apply inverse transformation to the predicted mask and save it as a NIfTI file.
        
        Parameters:
        - predicted_mask: Segmentation mask generated by the model
        - output_path: Path to save the inverse-transformed mask
        """
        # Apply inverse transformations to the predicted mask
        with mtf.allow_missing_keys_mode(self.transforms):
            inverted = self.transforms.inverse(
                {"image": self.transformed["image"], "seg": predicted_mask}
            )
        
        # Adjust dimension order [depth, height, width] -> [height, width, depth]
        inverted_mask = inverted["seg"].squeeze().permute(1, 2, 0).cpu().numpy()
        # Convert mask to uint8 and binarize
        inverted_mask = (inverted_mask > 0.5).astype(np.uint8)
        # Create a new NIfTI image object and save it
        nib.save(
            nib.Nifti1Image(inverted_mask, affine=self.affine, header=self.header), 
            output_path
        )
        print(f"Inverted mask saved to {output_path}")
        if get_noninver:
            nib.save(
                nib.Nifti1Image(predicted_mask.squeeze().permute(1, 2, 0).cpu().numpy(), 
                                affine=self.affine, header=self.header), 
                output_path.split(".")[0] + "_tf.nii.gz"
            )
            print(f"Non-inverted mask saved to {output_path.split('.nii.gz')[0] + '_tf.nii.gz'}")
    
    def save_transformed(self, output_path="."):
        if self.transformed is None:
            raise ValueError("Please apply transforms first before calling save_transformed.")
        transformed_image = self.transformed["image"].squeeze().permute(1, 2, 0).cpu().numpy()
        transformed_mask = self.transformed["seg"].squeeze().permute(1, 2, 0).cpu().numpy()
        
        # Save the NIfTI file
        nib.save(
            nib.Nifti1Image(transformed_image, affine=self.affine, header=self.header), 
            os.path.join(output_path, f"{self.ct_name}_tf.nii.gz")
        )
        nib.save(
            nib.Nifti1Image(transformed_mask, affine=self.affine, header=self.header), 
            os.path.join(output_path, f"{self.ct_name}_{self.mask_name}_tf.nii.gz")
        )
        print(f"Transformed image saved to {output_path}")
