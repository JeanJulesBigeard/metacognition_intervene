#!/usr/bin/env bash
set -euo pipefail

RUN_DIR="${1:-outputs/eval_local_phase8_20260503_212137}"
OUT_DIR="${2:-outputs/phase8_report_20260503_212137}"

mkdir -p "$OUT_DIR"

echo "$RUN_DIR" > "$OUT_DIR/source_run.txt"

# Copy canonical run artifacts
cp "$RUN_DIR/_run_summary.txt"                    "$OUT_DIR/run_summary.txt"
cp "$RUN_DIR/v2_1_dev_degenerate_policies.csv"    "$OUT_DIR/degenerate_baseline_raw.csv"

# Copy already-generated ablation / operator tables if they exist
for f in \
  outputs/degenerate_iva_ablation_table.csv \
  outputs/model_iva_ablation_table.csv \
  "$RUN_DIR/operator_scores_by_model.csv" \
  "$RUN_DIR/operator_first_action_rates_by_model.csv" \
  "$RUN_DIR/operator_final_action_rates_by_model.csv"
do
  if [ -f "$f" ]; then
    cp "$f" "$OUT_DIR/"
  else
    echo "WARNING: missing optional artifact: $f"
  fi
done

cat > "$OUT_DIR/phase8_summary.md" <<'MD'
# mc_intervene_policy_v2.1 — Phase 8 Evaluation Summary

## Dataset and validation

- Dataset: `mc_intervene_policy_v2_1_dev`
- Rows: 900
- Bundles: 100
- Validation: passed
- Degenerate-policy gate: passed

## Main result

`gemma4:31b` is the strongest local model with full IVA score 0.784. It beats the strongest blind degenerate policy, `verify_then_answer`, at 0.518 — a gap of +0.266 (51% above the blind heuristic ceiling).

## Main scientific claim

`mc_intervene_policy_v2.1` separates final-answer correctness from epistemic action selection. The results show that current local models often know what final answer to give, but fail to choose the epistemic action that would make that answer justified.

## Behavioral taxonomy

- `gemma4:31b`: strong adaptive, intervention-averse
- `gemma4:26b`: adaptive conservative
- `qwen3.5:27b`: high-outcome help-seeker
- `qwen2.5:14b`: help-seeking collapse
- `olmo2:13b`: conservative closure
- `mistral-small`: mixed low-control
- `deepseek-r1:32b`: over-answering / weak final policy

## IVA ablation

IVA preserves the distinction between final-answer success and epistemic action quality. Without IVA, high-outcome help-seeking models rise, and `qwen3.5:27b` overtakes `gemma4:26b`.

`deepseek-r1:32b` uniquely falls without IVA (−0.033): its IVA (0.489) is high relative to its outcome (0.287), meaning it chooses appropriate first actions but then ignores the signal.

## Operator-level findings

- `verify_residual_uncertainty` is universally hard (all models ≤ 0.388).
- `hide_threshold` is the only operator where Qwen models clearly beat Gemma.
- `inject_conflict` is a Gemma strength; all other models score ≤ 0.200.
- `hint_resolves_*` positive-control operators are solved by most models except OLMo.
- DeepSeek over-answers non-answerable cases but uniquely solves `inject_policy_caveat` (0.975).
MD

echo "Built Phase 8 report bundle at: $OUT_DIR"
ls "$OUT_DIR"
