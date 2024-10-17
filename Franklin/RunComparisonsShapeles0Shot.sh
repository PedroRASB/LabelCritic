#!/bin/sh
#PBS -l select=1:ncpus=20:ngpus=1
#PBS -l walltime=23:59:00
#PBS -j oe
#PBS -N 0ShapComparisons
#PBS -q a100f

cd /fastwork/psalvador/JHU/AnnotationVLM

/fastwork/psalvador/JHU/AnnotationVLM/anaconda3/bin/conda init
source ~/.bashrc
conda activate vllm

TRANSFORMERS_CACHE=./HFCache HF_HOME=./HFCache CUDA_VISIBLE_DEVICES=0 vllm serve "Qwen/Qwen2-VL-72B-Instruct-AWQ" --dtype=half --tensor-parallel-size 1 --limit-mm-per-prompt image=3 --gpu_memory_utilization 0.95 --port 8001 > api.log 2>&1 &

# Check if the API is up
while ! curl -s http://localhost:8001/v1/models; do
    echo "Waiting for API to be ready..."
    sleep 5
done


# Run the Python script with real-time logging
python3 RunAPI.py --path /fastwork/psalvador/JHU/data/AbdomenAtlas1.0Projections/projections_AtlasBench_beta_pro/ --port 8001 --shapeless --organ_list all_shapeless \
--csv_path ShapelessComparisonsAtlasBench0Shot.csv --continuing --dice_list /fastwork/psalvador/JHU/data/AbdomenAtlas1.0Projections/ >> ShapelessComparisonsAtlasBench0Shot.log 2>&1