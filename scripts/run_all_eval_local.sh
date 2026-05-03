#!/usr/bin/env bash
set -uo pipefail

# -----------------------------------------------------------------------------
# mc_intervene Phase 8 local evaluation runner
#
# Purpose:
#   1. Validate the v2.1 dev dataset.
#   2. Run degenerate-policy baselines.
#   3. Enforce degenerate-policy release gates.
#   4. Run full local model evaluations.
#   5. Save one output file per model plus a global run summary.
# -----------------------------------------------------------------------------

DATA_PATH="${DATA_PATH:-data/mc_intervene_policy_v2_1_dev/mc_intervene_policy_v2.csv}"
DATASET_NAME="${DATASET_NAME:-mc_intervene_policy_v2_1_dev}"
OUT_DIR="${OUT_DIR:-outputs/eval_local_phase8_$(date +%Y%m%d_%H%M%S)}"

# Full Phase 8 run defaults to the full v2.1 dev set.
# Override with LIMIT=100 ./scripts/run_all_eval_local.sh for a quick dry run.
LIMIT="${LIMIT:-900}"

# Set RUN_LARGE_MODELS=0 to only run the four core local models.
RUN_LARGE_MODELS="${RUN_LARGE_MODELS:-1}"

CORE_MODELS=(
  "qwen2.5:14b"
  "olmo2:13b"
  "mistral-small"
  "gemma4:26b"
)

LARGE_MODELS=(
  "qwen3.5:27b"
  "gemma4:31b"
  "deepseek-r1:32b"
)

MODELS=("${CORE_MODELS[@]}")
if [ "$RUN_LARGE_MODELS" = "1" ]; then
  MODELS+=("${LARGE_MODELS[@]}")
fi

mkdir -p "$OUT_DIR"
SUMMARY_FILE="$OUT_DIR/_run_summary.txt"
DEGENERATE_OUT="$OUT_DIR/v2_1_dev_degenerate_policies.csv"

get_timeout() {
  case "$1" in
    "gemma4:26b")      echo 3600 ;;
    "gemma4:31b")      echo 5400 ;;
    "qwen3.5:27b")     echo 3600 ;;
    "deepseek-r1:32b") echo 5400 ;;
    *)                 echo 1800 ;;
  esac
}

safe_model_name() {
  echo "$1" | tr ':/' '__'
}

log() {
  echo "$@" | tee -a "$SUMMARY_FILE"
}

run_step() {
  local name="$1"
  shift

  log "=================================================="
  log "$name"
  log "Started at: $(date)"
  log "=================================================="

  if "$@" 2>&1 | tee -a "$SUMMARY_FILE"; then
    log "SUCCESS: $name"
    log "Finished at: $(date)"
    log
    return 0
  else
    log "FAILED: $name"
    log "Finished at: $(date)"
    log
    return 1
  fi
}

# -----------------------------------------------------------------------------
# Header
# -----------------------------------------------------------------------------
{
  echo "Output directory: $OUT_DIR"
  echo "Data path: $DATA_PATH"
  echo "Dataset: $DATASET_NAME"
  echo "Limit: $LIMIT"
  echo "Run large models: $RUN_LARGE_MODELS"
  echo "Models: ${MODELS[*]}"
  echo "Started at: $(date)"
  echo
} | tee "$SUMMARY_FILE"

if [ ! -f "$DATA_PATH" ]; then
  log "ERROR: dataset not found at $DATA_PATH"
  exit 1
fi

# -----------------------------------------------------------------------------
# Phase 8 gate 1: dataset validation
# -----------------------------------------------------------------------------
run_step \
  "Dataset validation" \
  python scripts/validate_dataset.py \
    --data "$DATA_PATH" \
    --require-rich-action-diversity \
    --min-effect-count 25

if [ $? -ne 0 ]; then
  log "ABORT: dataset validation failed."
  exit 1
fi

# -----------------------------------------------------------------------------
# Phase 8 gate 2: degenerate baselines
# -----------------------------------------------------------------------------
run_step \
  "Degenerate-policy audit" \
  python scripts/eval_degenerate_policies.py \
    --data "$DATA_PATH" \
    --out "$DEGENERATE_OUT"

if [ $? -ne 0 ]; then
  log "ABORT: degenerate-policy audit failed."
  exit 1
fi

# -----------------------------------------------------------------------------
# Phase 8 gate 3: degenerate threshold release gate
# -----------------------------------------------------------------------------
run_step \
  "Degenerate-policy threshold gate" \
  python scripts/check_degenerate_thresholds.py \
    --data "$DEGENERATE_OUT"

if [ $? -ne 0 ]; then
  log "ABORT: degenerate-policy threshold gate failed."
  exit 1
fi

# -----------------------------------------------------------------------------
# Model evaluations
# -----------------------------------------------------------------------------
log "=================================================="
log "Model evaluation phase"
log "Started at: $(date)"
log "=================================================="
log

for model in "${MODELS[@]}"; do
  safe_name="$(safe_model_name "$model")"
  out_file="$OUT_DIR/${safe_name}.txt"
  model_timeout="$(get_timeout "$model")"

  log "=================================================="
  log "Running model: $model"
  log "Dataset: $DATASET_NAME"
  log "Limit: $LIMIT"
  log "Timeout: ${model_timeout}s"
  log "Output file: $out_file"
  log "Started at: $(date)"
  log "=================================================="

  if {
    echo "Model: $model"
    echo "Dataset: $DATASET_NAME"
    echo "Data path: $DATA_PATH"
    echo "Limit: $LIMIT  Timeout: ${model_timeout}s"
    echo "Started at: $(date)"
    echo

    python scripts/eval_local.py \
      --data "$DATA_PATH" \
      --provider ollama \
      --model "$model" \
      --limit "$LIMIT" \
      --timeout "$model_timeout"

    echo
    echo "Finished at: $(date)"
  } | tee "$out_file"; then
    log "SUCCESS: $model"
  else
    log "FAILED:  $model"
  fi

  log

done

log "All runs completed at $(date)"
log "Outputs saved in: $OUT_DIR"
log "Degenerate baseline CSV: $DEGENERATE_OUT"
