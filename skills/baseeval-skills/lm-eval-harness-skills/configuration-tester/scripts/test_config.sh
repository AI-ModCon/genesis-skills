#!/bin/bash
#
# Test script for lm-evaluation-harness configurations

set -euo pipefail

task_name="$1"
path_to_tasks="$2"
model="${3:-${LM_EVAL_MODEL:-hf}}"
model_args="${4:-${LM_EVAL_MODEL_ARGS:-pretrained=mistralai/Mistral-7B-Instruct-v0.3,dtype=float32}}"
limit="${5:-${LM_EVAL_LIMIT:-5}}"
run_llm_judge="${6:-${LM_EVAL_RUN_JUDGE:-false}}"

export LMEVAL_LOG_LEVEL=DEBUG

cmd=(
    lm_eval
    --model "$model"
    --model_args "$model_args"
    --include_path "$path_to_tasks"
    --tasks "$task_name"
    --limit "$limit"
    --log_samples
    --output_path "results/$task_name"
)

case "$run_llm_judge" in
    1|true|TRUE|yes|YES)
        cmd+=(--run_llm_judge)
        ;;
esac

"${cmd[@]}"
