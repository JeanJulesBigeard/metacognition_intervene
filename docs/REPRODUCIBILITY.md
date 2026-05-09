# Reproducibility — mc_intervene v2.1

## Dataset

| Property | Value |
|----------|-------|
| File | `data/mc_intervene_policy_v2_1_dev/mc_intervene_policy_v2.csv` |
| SHA-256 | `37e278860fd342f3f16ada41e8888e7dc6063d8ebd9e1d847cf042fd73c31208` |
| Rows | 900 |
| Bundles | 100 |
| Operators | 14 |
| Seed | 67 |

Regenerate from scratch:

```bash
mc-intervene-policy \
    --n-bundles 100 \
    --seed 67 \
    --out-dir data/mc_intervene_policy_v2_1_dev
```

Expected output: `mc_intervene_policy_v2.csv` (900 rows, 30 columns) plus `metadata.json`.

## Phase 8 evaluation run

| Property | Value |
|----------|-------|
| Run directory | `outputs/eval_local_phase8_20260503_212137` (git-ignored) |
| Models evaluated | 7 |
| Items per model | 900 |
| Scoring mode | `v2_1_full` (with IVA, with trajectory caps) |
| Seed | 42 |
| Date | 2026-05-03 |

Run all 7 models:

```bash
SEED=42 bash scripts/run_all_eval_local.sh
```

Run a single model:

```bash
python scripts/eval_local.py \
    --data data/mc_intervene_policy_v2_1_dev/mc_intervene_policy_v2.csv \
    --model gemma4:31b \
    --provider ollama \
    --base-url http://localhost:11434
```

## Dependencies

| Dependency | Role |
|------------|------|
| Python ≥ 3.10 | Runtime |
| `pandas` | Data handling |
| `pydantic` | Schema validation |
| `pyyaml` | Config parsing |
| [Ollama](https://ollama.com) | Local model inference |

Install the package and dependencies:

```bash
pip install -e .
```

## Model tags (Phase 8)

Models were pulled via `ollama pull`. The exact tags used in Phase 8:

| Model name | Ollama tag |
|------------|-----------|
| `gemma4:31b` | latest |
| `gemma4:26b` | latest |
| `qwen3.5:27b` | latest |
| `qwen2.5:14b` | latest |
| `mistral-small` | latest |
| `olmo2:13b` | latest |
| `deepseek-r1:32b` | latest |

Pull all models before running:

```bash
for m in gemma4:31b gemma4:26b qwen3.5:27b qwen2.5:14b mistral-small olmo2:13b deepseek-r1:32b; do
    ollama pull "$m"
done
```

## Release gate

After generating a new dataset version, run the degenerate-policy gate before publishing:

```bash
python scripts/eval_degenerate_policies.py \
    --data data/mc_intervene_policy_v2_1_dev/mc_intervene_policy_v2.csv \
    --out outputs/v2_dev_degenerate_policies.csv

python scripts/check_degenerate_thresholds.py
```

Exit code 0 = all baselines within ceiling. Exit code 1 = gate fails; do not publish.

## Report tables

Committed tables in `reports/tables/` are derived from the Phase 8 run:

| File | Description |
|------|-------------|
| `phase8_model_leaderboard.csv` | Per-model scores (both score families) |
| `model_iva_ablation_table.csv` | Model scores with and without IVA |
| `degenerate_baseline_table.csv` | Degenerate-policy baseline scores |
| `degenerate_iva_ablation_table.csv` | IVA ablation for degenerate policies |
| `operator_scores_by_model.csv` | Per-operator scores for all 7 models |
| `operator_first_action_rates_by_model.csv` | First-action distributions by operator |
| `operator_final_action_rates_by_model.csv` | Final-action distributions by operator |

Regenerate from raw per-item traces:

```bash
python scripts/build_phase8_tables.py \
    --phase8-dir outputs/eval_local_phase8_20260503_212137 \
    --degen-full outputs/v2_dev_degenerate_policies.csv \
    --degen-no-iva outputs/v2_dev_degenerate_policies_no_iva.csv
```
