#!/bin/bash
#
# Test script for lm-evaluation-harness configurations

set -euo pipefail

task_name="$1"
path_to_tasks="$2"
model="${3:-${LM_EVAL_MODEL:-hf}}"
model_args="${4:-${EVAL_MODEL_ARGS:-${LM_EVAL_MODEL_ARGS:-}}}"
if [ -z "$model_args" ]; then
  echo "error: EVAL_MODEL_ARGS is required. Ask the user which model to use and set it before running." >&2
  exit 64
fi
limit="${5:-${LM_EVAL_LIMIT:-5}}"
apply_chat_template="${6:-${LM_EVAL_APPLY_CHAT_TEMPLATE:-false}}"

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

if [ "$apply_chat_template" = "true" ]; then
    cmd+=(--apply_chat_template)
fi

"${cmd[@]}"
