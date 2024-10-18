from transformers import LlavaNextProcessor, LlavaNextForConditionalGeneration
import torch, os, csv, json
from tqdm import tqdm
import nibabel as nib
import numpy as np
from PIL import Image

task1 = {
    "file": "bad_labels_AbdomenAtlasBeta.json",
    "part": "errors_beta_full",
    "path": "/mnt/sdc/pedro/ErrorDetection/errors_beta_full",
    "label2": "Incorrect",
}
task2 = {
    "file": "bad_labels_nnUnet.json",
    "part": "errors_nnUnet_full",
    "path": "/mnt/sdc/pedro/ErrorDetection/errors_nnUnet_full",
    "label2": "Incorrect",
}
task3 = {
    "file": "good_labels_AbdomenAtlasBeta.json",
    "part": "good_labels_beta_full",
    "path": "/mnt/sdc/pedro/ErrorDetection/good_labels_beta_full",
    "label2": "Correct",
}

def step_1_q(organ):
    return (
        "The image I am sending is frontal projections of one CT scan, focusing on showing the bone. "
        "Look at it carefully, and answer the questions below:\n\n"
        "Q1- Which bones are on the top of the image? Bones are on its bottom?\n"
        "Q2- Which of the following landmarks are present in the image? Answer ‘yes’ or ‘no’ using the template below, substituting _ by Yes or No:\n"
        "skull = _ "
        "neck = _ "
        "trachea = "
        "_ribs = _ "
        "lumbar spine = _ "
        "pelvis = _ "
        "femurs = _ \n"
        "Q3- Considering these landmarks and the bones on the image top and bottom, "
        "give me a complete list of all organs (not bones) usually contained within this image "
        "limits (just list their names).\n"
        f"Q4- Based on your answer to Q3, is the {organ} usually present within this image limits? "
        "Answer ‘yes’ or ‘no’ using the template below, substituting  _ by Yes or No:\n"
        "Q4 = _"
    )

def step_2_q(organ):
    return (
        "The image I am sending is a frontal projection of a CT scan. "
        "It is not a CT slice, we have transparency and can see through the entire body, "
        "like a X-ray. The left side of the image represents the right side of the human body. "
        f"The {organ} region in the image should be marked in red, "
        "using an overlay. However, I am not sure if the red overlay correctly "
        f"or incorrectly marks the {organ}. Please following these instructions:\n\n"
        f"1. Check if the red region is coherent with the expected shape and location of a {organ}."
        "Show your reasoning in the answer.\n"
        "2. After checking, you should give an final judge in the end of your answer, substituting _ by Good or Bad:\n"
        "Annotation = _"
    )

def inference(image_path, question, device, mute=True):
    image = Image.open(image_path)
    conversation = [
        {
          "role": "user",
          "content": [
              {"type": "text", "text": question},
              {"type": "image"},
            ],
        },
    ]
    prompt = processor.apply_chat_template(conversation, add_generation_prompt=True)
    inputs = processor(images=image, text=prompt, return_tensors="pt").to(device)

    # autoregressively complete prompt
    output = model.generate(**inputs, max_new_tokens=256)
    answer = processor.decode(output[0], skip_special_tokens=True).split("[/INST]")[1].strip()

    if not mute:
        print("*" * 80)
        print("Question:")
        print(question)
        print("=" * 50)
        print("Answer:")
        print(answer)
        print("*" * 80)
    return answer

def check_step1(answer):
    try:
        judge = answer.split("Q4")[1].lower()
        return "present" if "yes" in judge else "no"
    except:
        return "no"

def check_step2(answer):
    try:
        judge = answer.split("Annotation")[1].lower()
        return "Correct" if "good" in judge else "Incorrect"
    except:
        return "Incorrect"
    
def check_step1_label(case, organ, path="/mnt/T9/AbdomenAtlasPro"):
    if organ == "kidneys":
        temp1 = nib.load(os.path.join(path, case, "segmentations", "kidney_left.nii.gz")).get_fdata()
        temp2 = nib.load(os.path.join(path, case, "segmentations", "kidney_right.nii.gz")).get_fdata()
        temp = temp1 + temp2
        # temp = np.maximum(temp1, temp2)
    else:
        temp = nib.load(os.path.join(path, case, "segmentations", f"{organ}.nii.gz")).get_fdata()
    # check whether is all zero
    return "no" if np.all(temp == 0) else "present"

task1 = {
    "file": "bad_labels_AbdomenAtlasBeta.json",
    "part": "errors_beta_full",
    "path": "/mnt/sdc/pedro/ErrorDetection/errors_beta_full",
    "label2": "Incorrect",
}
task2 = {
    "file": "bad_labels_nnUnet.json",
    "part": "errors_nnUnet_full",
    "path": "/mnt/sdc/pedro/ErrorDetection/errors_nnUnet_full",
    "label2": "Incorrect",
}
task3 = {
    "file": "good_labels_AbdomenAtlasBeta.json",
    "part": "good_labels_beta_full",
    "path": "/mnt/sdc/pedro/ErrorDetection/good_labels_beta_full",
    "label2": "Correct",
}

def append_dict_to_csv(dict_data, csv_path):
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=dict_data.keys())
        if file.tell() == 0:
            writer.writeheader()
        writer.writerow(dict_data)

def get_one_result(task, case, organ):
    question1 = step_1_q(organ)
    question2 = step_2_q(organ)
    try:
        image1_path = os.path.join(task["path"], organ, f"{case}_ct_window_bone_axis_1.png")
        answer1 = inference(image1_path, question1, device)
    except:
        image1_path = os.path.join(task["path"], organ, f"{case}_ct_window_bone_axis_1_{organ}.png")
        answer1 = inference(image1_path, question1, device)
    image2_path = os.path.join(task["path"], organ, f"{case}_overlay_window_bone_axis_1_{organ}_y1.png")
    answer2 = inference(image2_path, question2, device)
    judge1 = check_step1(answer1)
    judge2 = check_step2(answer2)
    label1 = check_step1_label("BDMAP_00000055", organ)
    label2 = task["label2"]
    
    task_raw = {
        "sample": case,
        "organ": organ,
        "part": task["part"],
        "question1": question1,
        "answer1": answer1,
        "question2": question2,
        "answer2": answer2,
    }
    task_single = {
        "sample": case,
        "organ": organ,
        "part": task["part"],
        "result step 1": judge1,
        "label step 1": label1,
        "result step 2": judge2,
        "label step 2": label2,
    }
    return task_raw, task_single

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", type=str, default="cuda:1")
    parser.add_argument("--task", type=int, default=1)
    args = parser.parse_args()
    
    device = args.device
    model_path = '/mnt/sdh/qwu59/ckpts/llava-v1.6-mistral-7b-hf'
    result_path = "results/llava/"
    processor = LlavaNextProcessor.from_pretrained(model_path)
    model = LlavaNextForConditionalGeneration.from_pretrained(model_path, torch_dtype=torch.float16, low_cpu_mem_usage=True) 
    model = model.to(device)
    
    if args.task == 1:
        task = task1
    elif args.task == 2:
        task = task2
    elif args.task == 3:
        task = task3
        
    with open(task["file"]) as f:
        task_data = json.load(f)
        
    for organ in tqdm(task_data):
        for case in tqdm(task_data[organ]):
            # check whether the case exists in the final csv
            check_table = os.path.join(result_path, "final", f"{task['part']}.csv")
            skip_sign = False
            if os.path.exists(check_table):
                with open(check_table, mode='r') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        if row["sample"] == case and row["organ"] == organ:
                            skip_sign = True
                            break
            if skip_sign:
                continue
            
            # inference new case
            task_raw, task_single = get_one_result(task, case, organ)
            print(task_single)
            append_dict_to_csv(task_raw, os.path.join(result_path, "raw", f"{task['part']}.csv"))
            append_dict_to_csv(task_single, os.path.join(result_path, "final", f"{task['part']}.csv"))
    