# Use LVLM to compare the per-voxel organ annotations of 2 semantic segmenters

### Installation and running

Install
```bash
git clone https://github.com/PedroRASB/AnnotationVLM
cd AnnotationVLM
conda create -n lmdeploy python=3.11
conda activate lmdeploy
conda install ipykernel
conda install pip
pip install -r requirements.txt
```

Deploy API locally (tp should be the number of GPUs, and it accepts only powers of 2)
```bash
mkdir HFCache
export TRANSFORMERS_CACHE=./HFCache
export HF_HOME=./HFCache
CUDA_VISIBLE_DEVICES=1,2,3,4 lmdeploy serve api_server OpenGVLab/InternVL2-llama3-76B-AWQ --backend turbomind --server-port 23333 --model-format awq --tp 4 --session-len 8192 --cache-max-entry-count 0.1
#play with --cache-max-entry-count to change memory cost. It varies between 0 and 1, and higher numbers increase memory consumption. Default: --cache-max-entry-count 0.8
```

Call API (Python)
```python
import ErrorDetector as ed

ct='path/to/ct.nii.gz'
y1='path/to/segmentation_1.nii.gz'
y2='path/to/segmentation_2.nii.gz'

answer=ed.project_and_compare(ct,y1,y2)
```
Example: see MyAPITest.ipynb

