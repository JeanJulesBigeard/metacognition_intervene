#!/usr/bin/env bash
set -uo pipefail

DATA_PATH="data/mc_intervene_dataset_v1/mc_intervene_eval.csv"
OUT_DIR="outputs/eval_local_$(date +%Y%m%d_%H%M%S)"

mkdir -p "$OUT_DIR"

MODELS=(
  "qwen2.5:14b"
  "olmo2:13b"
  "mistral-small"
  "gemma4:26b"
  "qwen3.5:27b"
  "gemma4:31b"
  "deepseek-r1:32b"
)

get_limit() {
  case "$1" in
    "gemma4:26b")      echo 100  ;;
    "gemma4:31b")      echo 100  ;;
    "qwen3.5:27b")     echo 100  ;;
    "deepseek-r1:32b") echo 100  ;;
    *)                 echo 100 ;;
  esac
}

get_timeout() {
  case "$1" in
    "gemma4:26b")      echo 3600 ;;
    "gemma4:31b")      echo 3600 ;;
    "qwen3.5:27b")     echo 2400 ;;
    "deepseek-r1:32b") echo 3600 ;;
    *)                 echo 1800 ;;
  esac
}

echo "Output directory: $OUT_DIR" | tee "$OUT_DIR/_run_summary.txt"
echo "Data path: $DATA_PATH"      | tee -a "$OUT_DIR/_run_summary.txt"
echo                               | tee -a "$OUT_DIR/_run_summary.txt"

for model in "${MODELS[@]}"; do
  safe_name="$(echo "$model" | tr ':/' '__')"
  out_file="$OUT_DIR/${safe_name}.txt"
  model_limit="$(get_limit "$model")"
  model_timeout="$(get_timeout "$model")"

  echo "==================================================" | tee -a "$OUT_DIR/_run_summary.txt"
  echo "Running model: $model"        | tee -a "$OUT_DIR/_run_summary.txt"
  echo "Limit: $model_limit  Timeout: ${model_timeout}s" | tee -a "$OUT_DIR/_run_summary.txt"
  echo "Output file: $out_file"       | tee -a "$OUT_DIR/_run_summary.txt"
  echo "Started at: $(date)"          | tee -a "$OUT_DIR/_run_summary.txt"
  echo "==================================================" | tee -a "$OUT_DIR/_run_summary.txt"

  if {
    echo "Model: $model"
    echo "Limit: $model_limit  Timeout: ${model_timeout}s"
    echo "Started at: $(date)"
    echo

    python scripts/eval_local.py \
      --data "$DATA_PATH" \
      --provider ollama \
      --model "$model" \
      --limit "$model_limit" \
      --timeout "$model_timeout"

    echo
    echo "Finished at: $(date)"
  } | tee "$out_file"; then
    echo "SUCCESS: $model" | tee -a "$OUT_DIR/_run_summary.txt"
  else
    echo "FAILED:  $model" | tee -a "$OUT_DIR/_run_summary.txt"
  fi

  echo | tee -a "$OUT_DIR/_run_summary.txt"
done

echo "All runs completed at $(date)" | tee -a "$OUT_DIR/_run_summary.txt"