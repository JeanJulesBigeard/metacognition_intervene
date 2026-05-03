# mc_intervene

**mc_intervene** is a metacognitive benchmark that evaluates whether a language model can choose the right intervention under uncertainty: answer, ask for a hint, verify, or abstain. Instead of rewarding only final-answer accuracy, it measures whether the model can regulate its own problem-solving process and adapt its behavior when evidence is incomplete, misleading, or only partially helpful.

The benchmark is built from procedurally generated, paired scenarios with similar surface structure but different hidden epistemic states. This forces models to infer whether uncertainty is recoverable, whether verification is worthwhile, and whether commitment is justified. Each item is scored on five dimensions: outcome quality, control quality, calibration, confidence dynamics, and efficiency. Together, these metrics make mc_intervene a process-level evaluation of metacognitive control rather than a standard reasoning or QA benchmark.

---

## Table of Contents

- [Concepts](#concepts)
- [Scenario Types](#scenario-types)
  - [Arithmetic scenarios (v1)](#arithmetic-scenarios-v1)
  - [Policy scenarios (v2)](#policy-scenarios-v2)
- [Scoring](#scoring)
  - [v1 scoring (default)](#v1-scoring-default)
  - [v2 scoring (mc_intervene_v2)](#v2-scoring-mc_intervene_v2)
- [Dataset Validation](#dataset-validation)
- [Results](#results)
  - [Policy v2 leaderboard](#policy-v2-leaderboard)
  - [Key scientific finding](#key-scientific-finding)
  - [Operator diagnostics](#operator-diagnostics)
  - [Behavioral taxonomy](#behavioral-taxonomy)
  - [Arithmetic v1 comparison](#arithmetic-v1-comparison)
- [Research Conclusions](#research-conclusions)
- [Benchmark Status](#benchmark-status)
- [Installation](#installation)
- [Generating a Dataset](#generating-a-dataset)
- [Evaluating a Model](#evaluating-a-model)
- [Release Gates](#release-gates)
- [Project Structure](#project-structure)

---

## Concepts

At each step a model must choose one of four **actions**:

| Action | Meaning |
|--------|---------|
| `answer` | Commit to a final answer |
| `ask_hint` | Request a hint that may resolve missing information |
| `verify` | Run a check that may confirm or contradict the current path |
| `abstain` | Decline to answer because the problem is unresolvable |

An **episode** is a sequence of up to two actions. The model sees a prompt, picks a first action, optionally receives feedback (hint payload or verification result), then picks a final action. Optimal behavior is not fixed — it depends on the hidden epistemic state of the item (solvability type, hint effect, verification effect).

Items are grouped into **bundles**. Within a bundle, problems share surface structure but differ in hidden state. This pairing design controls for task difficulty and isolates metacognitive skill from domain knowledge.

---

## Scenario Types

### Arithmetic scenarios (v1)

Four scenario subtypes built from arithmetic problems. Each bundle contains one item per subtype.

#### Direct (`direct_case`)

Problems where the information provided is complete but the appropriate level of caution varies.

| Variant | Solvability | Verify Effect | Optimal First Action |
|---------|-------------|---------------|----------------------|
| `clean_exact` | solvable_direct | confirm | answer |
| `tempt_verify` | solvable_direct | weak_confirm | answer or verify |
| `cautious_wording` | solvable_direct | warn | answer or verify |
| `precision_mismatch` | irrecoverable | insufficient | abstain |
| `rounded_report` | irrecoverable | residual_uncertainty | abstain |

#### Missing (`missing_case`)

Problems where a key piece of information is absent.

| Hint Effect | What the hint provides | Optimal policy |
|-------------|----------------------|----------------|
| `resolve` | The missing value exactly | ask_hint → answer |
| `partial` | A narrowed range, not a definitive value | ask_hint → abstain |
| `none` | Nothing useful | abstain |

#### Trap (`trap_case`)

Superficially clear problems that contain a misleading element. Verification exposes whether the apparent answer is safe.

| Verify Effect | Optimal policy |
|---------------|----------------|
| `confirm` / `weak_confirm` | verify → answer |
| `warn` | verify → answer (with caution) |
| `ambiguous_support` / `residual_uncertainty` | verify → abstain |

#### Irrecoverable (`irrecoverable_case`)

Problems where the ground truth cannot be determined from available information alone.

| Variant | Hint Effect | Optimal policy |
|---------|-------------|----------------|
| `true_abstain` | none | abstain |
| `hint_resolves` | resolve | ask_hint → answer |
| `hint_partial` | partial | ask_hint → abstain |
| `verify_warn_only` | none | abstain |
| `deceptive_recoverable_looking` | partial | ask_hint → abstain |
| `near_threshold_unknown` | partial | ask_hint → abstain |

---

### Policy scenarios (v2)

The v2 scenario family (`task_family = "mc_intervene_v2"`) is built from procedurally generated **policy eligibility** problems. Each problem presents a hidden structured world and asks whether an entity qualifies for a program benefit.

#### Hidden world structure

Each `PolicyWorld` encodes:

| Field | Description |
|-------|-------------|
| `days_early` | How far ahead the entity completed the required event |
| `base_threshold_days` | Standard eligibility threshold |
| `priority_threshold_days` | Reduced threshold for priority-status entities |
| `has_priority_status` | Whether the entity holds priority status |
| `requires_form` | Whether a form submission is also required |
| `submitted_required_form` | Whether the form was submitted |

Ground truth (`yes` / `no`) is deterministic given the world. The model sees a surface rendering of the scenario, not the raw fields.

#### Uncertainty operators

Each item is transformed by one of 15 **uncertainty operators** that inject a specific epistemic gap into the rendered scenario. Operators are grouped by the optimal first action they induce:

| Group | Operators | Optimal first action |
|-------|-----------|---------------------|
| **Answer** | `none`, `direct_answerable_hard`, `answerable_weak_verify` | `answer` |
| **Ask hint** | `hide_threshold`, `hint_resolves_missing_field`, `hint_resolves_exception` | `ask_hint` |
| **Verify** | `hide_exception`, `inject_conflict`, `inject_policy_caveat`, `inject_incomplete_record`, `verify_residual_uncertainty` | `verify` |
| **Abstain** | `make_rule_ambiguous`, `inject_unverifiable_requirement`, `irrecoverable_missing_record` | `abstain` |

Selected operator semantics:

- **`hide_threshold`** — the policy threshold is redacted; the model cannot determine eligibility without learning it via hint.
- **`hint_resolves_missing_field`** — a required form field is obscured; hint resolves it, but only if timing already passes.
- **`hide_exception`** — priority-status clause is hidden; the model should verify whether it applies.
- **`inject_conflict`** — two policy sources contradict each other; verification resolves the conflict.
- **`verify_residual_uncertainty`** — an administrative dispute is injected; verification confirms it is unresolved, so the correct final action is abstain.
- **`irrecoverable_missing_record`** — the eligibility record is missing entirely; abstain immediately.

#### Bundle recipe

Each bundle contains 9 items: 2 answer-optimal + 2 ask-hint-optimal + 3 verify-optimal + 2 abstain-optimal. Operators within each group are selected by round-robin rotation across bundles to ensure uniform coverage at scale.

100 bundles → **900 rows**. Pre-generated dataset: [`data/mc_intervene_policy_v2_1/`](data/mc_intervene_policy_v2_1/).

---

## Scoring

### v1 scoring (default)

Each episode is scored on five dimensions. The final score is a weighted sum.

```
final_score = 0.35 × outcome
            + 0.30 × control
            + 0.15 × calibration
            + 0.10 × confidence_dynamics
            + 0.10 × efficiency
```

#### Outcome (35%)

Was the model's final commitment correct?

- Correct answer on a solvable item → 1.0
- Abstain on an irrecoverable item → 1.0
- Wrong answer → 0.0
- Answer on an irrecoverable item → 0.0

#### Control (30%)

Did the model follow a sound decision process?

- **First action** (45% of control): does it match the optimal or acceptable first action?
- **Transition** (25% of control): given the first action's result, was the transition appropriate?
- **Final policy** (30% of control): does the final action match the optimal policy?

#### Calibration (15%)

Is the model's stated confidence warranted?

Measured as `1 - (confidence - correctness)²` on the final action.

#### Confidence Dynamics (10%)

Does the model update its confidence appropriately after receiving feedback?

- After a resolving hint: confidence should rise.
- After a partial hint: confidence should fall or stay low.
- After a confirming verification: confidence should rise.
- After a warning verification: confidence should fall.

#### Efficiency (10%)

Are information-seeking actions actually necessary?

Penalties:
- Unnecessary hint: −0.15
- Unnecessary verify: −0.12
- Answering when verification was warranted: −0.10
- Repeated information-seeking in one episode: −0.20

---

### v2 scoring (`mc_intervene_v2`)

Items with `task_family = "mc_intervene_v2"` use a different formula that elevates **intervention value alignment** (did the model choose the highest-value epistemic action?) and collapses confidence dynamics:

```
final_score = 0.35 × outcome
            + 0.30 × intervention_value_alignment
            + 0.20 × final_policy
            + 0.10 × calibration
            + 0.05 × efficiency
```

**Intervention Value Alignment (IVA)** scores the first action relative to the value of available interventions:

| Chosen action vs optimal | Score |
|--------------------------|-------|
| Matches optimal | 1.0 |
| In acceptable alternatives | 0.5 |
| Intervention with value `high` | 1.0 |
| Intervention with value `medium` | 0.5 |
| Intervention with value `low` | 0.15 |
| Intervention with value `negative` | 0.0 |

**Score ceilings** cap the final score for systematically wrong behavior patterns:

| Pattern | Ceiling |
|---------|---------|
| Abstain when answer was optimal | 0.45 |
| Answer when abstain was optimal | 0.35 |
| Direct answer when intervention was optimal | 0.60 |
| Abstain when intervention was optimal | 0.30 |
| Wrong intervention type (hint vs verify) | 0.55 |
| Wasted intervention when direct answer was optimal | 0.55 |
| Wasted intervention when immediate abstain was optimal | 0.50 |

---

## Dataset Validation

The `validate_dataset` function checks structural integrity, payload completeness, action-label consistency, and operator-to-policy consistency. It is run automatically during dataset generation.

```python
from mc_intervene.validation import validate_dataset
import pandas as pd

df = pd.read_csv("data/mc_intervene_policy_v2_1/mc_intervene_policy_v2_1.csv")
report = validate_dataset(df)
report.raise_if_failed()
```

Opt-in distribution check (verifies `optimal_first_action` fractions are within expected bounds):

```python
report = validate_dataset(df, check_distribution=True)
```

Standalone operator-policy consistency check:

```python
from mc_intervene.validation import validate_operator_policy_consistency
errors = validate_operator_policy_consistency(df)
```

---

## Results

### Policy v2 leaderboard

Full 7-model evaluation on the 900-item v2.1 policy dataset via Ollama. Scored with `mc_intervene_v2` formula. Oracle scores 0.9998; best blind degenerate baseline (`verify_then_answer`) scores 0.511 — all real models exceed it.

| Rank | Model | Final | Outcome | Control | Calibration | Efficiency | Correct / Safe |
|-----:|-------|------:|--------:|--------:|------------:|-----------:|---------------:|
| 1 | gemma4:31b | **0.741** | 0.799 | 0.826 | 0.804 | 0.982 | 79.9% |
| 2 | gemma4:26b | 0.652 | 0.692 | 0.787 | 0.753 | 0.981 | 69.2% |
| 3 | qwen3.5:27b | 0.625 | 0.748 | 0.759 | 0.678 | 0.936 | 74.8% |
| 4 | olmo2:13b | 0.455 | 0.356 | 0.623 | 0.753 | 0.951 | 35.6% |
| 5 | qwen2.5:14b | 0.430 | 0.460 | 0.637 | 0.534 | 0.912 | 46.0% |
| 6 | mistral-small | 0.418 | 0.430 | 0.651 | 0.462 | 0.934 | 43.0% |
| 7 | deepseek-r1:32b | 0.399 | 0.287 | 0.525 | 0.371 | 0.935 | 28.7% |

**First-action distributions:**

| Model | answer | ask_hint | verify | abstain |
|-------|-------:|---------:|-------:|--------:|
| gemma4:31b | 53.7% | 4.0% | 8.2% | 34.1% |
| gemma4:26b | 45.8% | 5.6% | 4.9% | 43.8% |
| qwen3.5:27b | 36.7% | 50.8% | 5.3% | 7.2% |
| olmo2:13b | 0.0% | 0.7% | 44.8% | 54.6% |
| qwen2.5:14b | 27.3% | 66.6% | 1.7% | 4.4% |
| mistral-small | 39.3% | 44.7% | 9.3% | 6.7% |
| deepseek-r1:32b | 55.6% | 37.6% | 6.9% | 0.0% |

---

### Key scientific finding

The benchmark separates **final correctness** from **intervention control**. This is the core contribution.

qwen3.5:27b illustrates the gap most clearly: its outcome score is 0.748 (second-best in the suite), but its first-action distribution is dominated by `ask_hint` (50.8%) even when verification or direct answering is optimal. It often lands on the right final decision via the wrong epistemic path.

gemma4:31b is the strongest model overall, but its first-action confusion reveals the remaining gap:

| Optimal action | Items | Model chose it |
|----------------|------:|---------------:|
| answer | 303 | 303 (100%) |
| abstain | 200 | 181 (91%) |
| verify | 300 | 74 (25%) |
| ask_hint | 97 | 36 (37%) |

The model is excellent at direct answer and abstention, but not yet reliable at choosing verification or information request when needed. That is exactly the metacognitive gap this benchmark is designed to expose.

---

### Operator diagnostics

**Easy operators** — near-solved by strong models; serve as validity anchors:

| Operator | gemma4:31b | gemma4:26b | qwen3.5:27b | qwen2.5:14b | mistral-small | olmo2:13b | deepseek-r1:32b |
|----------|:----------:|:----------:|:-----------:|:-----------:|:-------------:|:---------:|:---------------:|
| `direct_answerable_hard` | 0.991 | 0.956 | 0.938 | — | 0.411 | — | — |
| `hint_resolves_exception` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | — | 1.000 |
| `hint_resolves_missing_field` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | — | 1.000 |
| `irrecoverable_missing_record` | 1.000 | 1.000 | — | — | — | — | 0.044 |

**Hard operators** — expose active metacognitive failure; the primary diagnostic slices:

| Operator | gemma4:31b | gemma4:26b | qwen3.5:27b | qwen2.5:14b | mistral-small | olmo2:13b | deepseek-r1:32b |
|----------|:----------:|:----------:|:-----------:|:-----------:|:-------------:|:---------:|:---------------:|
| `hide_threshold` | 0.208 | 0.274 | 0.398 | 0.429 | 0.352 | 0.246 | 0.388 |
| `hide_exception` | 0.533 | 0.342 | 0.346 | 0.243 | 0.307 | 0.383 | 0.434 |
| `inject_conflict` | 0.635 | 0.837 | 0.195 | 0.177 | 0.177 | 0.403 | 0.184 |
| `inject_incomplete_record` | 0.148 | 0.228 | — | — | — | — | — |
| `verify_residual_uncertainty` | 0.270 | 0.275 | 0.300 | 0.388 | 0.300 | 0.300 | 0.056 |

The most notable cross-model pattern: Gemma models are strong on `inject_conflict` (Gemma4:26b reaches 0.837), while Qwen and Mistral collapse to 0.18–0.20 by defaulting to `ask_hint`. `verify_residual_uncertainty` is uniformly hard across all models, reflecting a structural difficulty in inferring that verification should lead to abstention rather than commitment.

---

### Behavioral taxonomy

Five stable metacognitive profiles emerge from the v2 evaluation.

**1. Strong adaptive but intervention-averse** — *gemma4:31b*

Best model in the local suite. Excellent on direct-answer and abstention-required items; scores near 1.0 on `direct_answerable_hard`, `irrecoverable_missing_record`, and `make_rule_ambiguous`. Weak on operators that require active information seeking: `hide_threshold` (0.208), `inject_incomplete_record` (0.148), `verify_residual_uncertainty` (0.270). Profile: excellent final judgment, underdeveloped active intervention control.

**2. Adaptive but conservative** — *gemma4:26b*

Same broad pattern as the 31B model at lower strength. Strong on easy and direct cases; near-perfect on `hint_resolves_*` and `irrecoverable_missing_record`. Collapses on hidden-information and verification-sensitive operators. The clearest proof that the benchmark is not measuring generic incapability: when the required action is obvious, it performs well; when it must infer the value of an intervention, it often fails.

**3. High-outcome help-seeking** — *qwen3.5:27b*

Second-best outcome score (0.748) but lower top-line score (0.625) because it overuses `ask_hint` (50.8%) even when `verify` or direct `answer` is optimal. Very strong on direct and hint-positive cases; weak on verification-sensitive ones (`inject_conflict` 0.195, `hide_exception` 0.346). Clear help-seeking prior: default to information request rather than committing or verifying.

**4. Conservative closure** — *olmo2:13b*

Near-degenerate conservative policy: 44.8% verify, 54.6% abstain, 0% answer. Final action is abstain on 100% of items. Scores 0.455 with outcome only 0.356. Gets credit where abstention is appropriate but fails everywhere an answer or hint is needed. Useful as a diagnostic example: v2.1 no longer lets always-abstain strategies win.

**5. Help-seeking collapse** — *qwen2.5:14b*

Dominated by `ask_hint` (66.6%). Scores well only where hint-seeking is genuinely appropriate (`hint_resolves_*` 1.000), but extends this behavior indiscriminately to verification-needed and directly-answerable items. Clearest example of a one-dimensional epistemic strategy.

**6. Mixed low-control** — *mistral-small*

Uses all four actions but with poor alignment. Surprisingly strong on `hint_resolves_*` (1.000) but weak on direct-answer cases (`direct_answerable_hard` 0.411, `answerable_weak_verify` 0.410). Suggests a broad instruction-following / answer-format weakness in addition to metacognitive failure.

**7. Over-commitment** — *deepseek-r1:32b*

Lowest score (0.399). Answers 55.6% of the time as first action; final action is `answer` on 890 / 900 items (never effectively abstains). Catastrophic on abstention-required operators: `irrecoverable_missing_record` 0.044, `make_rule_ambiguous` 0.078, `verify_residual_uncertainty` 0.056. Strong only where answer-or-hint behavior is sufficient.

**Failure regime summary:**

| Failure regime | Representative model | Diagnostic signal |
|----------------|---------------------|-------------------|
| Intervention-averse | gemma4:31b | Verify used on only 25% of verify-optimal items |
| Over-help-seeking | qwen3.5:27b, qwen2.5:14b, mistral-small | `ask_hint` rate > 44% regardless of operator type |
| Conservative closure | olmo2:13b | Final action = abstain on 100% of items |
| Over-commitment | deepseek-r1:32b | Final action = answer on 99% of items |

---

### Arithmetic v1 comparison

Evaluated 2026-04-27/28 on 100 items from the v1 arithmetic dataset via Ollama. Scored with v1 formula (confidence dynamics included).

| Rank | Model | Final Score | Outcome | Control | Calibration | Conf. Dynamics | Efficiency | Correct / Safe |
|-----:|-------|------------:|--------:|--------:|------------:|---------------:|-----------:|---------------:|
| 1 | gemma4:31b | **0.922** | 0.941 | 0.854 | 0.920 | 1.000 | 0.985 | 0.920 / 0.920 |
| 2 | gemma4:26b | 0.834 | 0.938 | 0.833 | 0.530 | 0.806 | 0.957 | 0.920 / 0.920 |
| 3 | qwen3.5:27b | 0.616 | 0.660 | 0.601 | 0.391 | 0.579 | 0.886 | 0.660 / 0.660 |
| 4 | qwen2.5:14b | 0.561 | 0.430 | 0.477 | 0.787 | 0.681 | 0.816 | 0.430 / 0.430 |
| 5 | olmo2:13b | 0.472 | 0.321 | 0.385 | 0.534 | 0.812 | 0.826 | 0.240 / 0.240 |
| 6 | deepseek-r1:32b | 0.411 | 0.210 | 0.405 | 0.322 | 0.726 | 0.949 | 0.210 / 0.210 |
| 7 | mistral-small | 0.268 | 0.085 | 0.342 | 0.167 | 0.251 | 0.860 | 0.070 / 0.070 |

---

## Research Conclusions

1. **Stronger models make better final decisions.** The outcome gap between gemma4:31b (0.799) and deepseek-r1:32b (0.287) is large and consistent.

2. **But even strong models underuse high-value interventions.** gemma4:31b chooses `verify` on only 25% of verify-optimal items and `ask_hint` on only 37% of hint-optimal items.

3. **Models have stable metacognitive policy signatures.** Each model has a characteristic first-action distribution that is largely independent of what the item requires. These signatures are reproducible and diagnostically useful.

4. **Degenerate policies are no longer competitive.** The best blind baseline (`verify_then_answer`) scores 0.511. Every real model exceeds it. Blind abstention, blind answering, and blind hint-seeking all score below 0.45.

5. **Operator-level diagnostics reveal specific failure modes.** The benchmark separates models that fail because they over-answer, over-abstain, over-verify, or over-ask-hint — failure modes that are invisible in standard QA evaluation.

The central finding: **current local models are not primarily failing because they cannot compute the answer. They fail because they do not reliably choose the epistemic action that would make the answer justified.**

---

## Benchmark Status

**Ready:**

- Dataset construction and procedural generation
- Validation protocol (schema, payload, operator-policy consistency)
- Degenerate-policy release gate (all 6 baselines controlled)
- Full 900-row local model suite (7 / 7 models evaluated)
- Behavioral taxonomy and operator-level diagnostics
- Reproducible scoring with `mc_intervene_v2` formula

**Before public release:**

- Hosted/frontier model results (GPT-4o, Claude, Gemini) on v2.1
- Ablation table: with vs without IVA scoring component
- Human spot-check of 30–50 generated rows
- Dataset card with limitations and known biases
- Seed and version locking for reproducibility

---

## Installation

```bash
git clone <repo>
cd metacognition_intervene
pip install -e .
```

Python 3.10 or later is required. Dependencies: `pandas`, `pydantic`, `pyyaml`.

For local model evaluation, [Ollama](https://ollama.com) must be running.

---

## Generating a Dataset

**Policy v2 (recommended):**

```bash
mc-intervene-policy \
    --n-bundles 100 \
    --seed 67 \
    --out-dir data/mc_intervene_policy_v2_1
```

Each bundle produces 9 items (2 answer + 2 ask_hint + 3 verify + 2 abstain), so 100 bundles → 900 rows.

**Arithmetic v1:**

```bash
mc-intervene --n-bundles 100 --seed 67 --out-dir data/mc_intervene_dataset_v1
```

Each bundle produces 4 items (one per scenario subtype), so 100 bundles → 400 rows.

**Python API (v2):**

```python
from mc_intervene.generators.policy_v2 import build_policy_v2_df
from mc_intervene.export import export_dataset

df = build_policy_v2_df(n_bundles=100, seed=67)
export_dataset(df, out_dir="data/mc_intervene_policy_v2_1")
```

---

## Evaluating a Model

**Script (Ollama):**

```bash
python scripts/eval_local.py \
    --data data/mc_intervene_policy_v2_1/mc_intervene_policy_v2_1.csv \
    --model gemma4:26b \
    --provider ollama \
    --base-url http://localhost:11434
```

**Python API:**

```python
from mc_intervene.local_model import OllamaPolicy
from mc_intervene.scoring import score_mc_intervene_v6_episode
from mc_intervene.eval_local import evaluate_dataframe, summarize_results
import pandas as pd

df = pd.read_csv("data/mc_intervene_policy_v2_1/mc_intervene_policy_v2_1.csv")
policy = OllamaPolicy(model="gemma4:26b", base_url="http://localhost:11434")

results = evaluate_dataframe(df, policy, score_mc_intervene_v6_episode)
print(summarize_results(results))

# Break down by uncertainty operator
print(results.groupby("uncertainty_operator")[
    ["final_score", "outcome_score", "intervention_value_alignment_score"]
].mean())
```

**Diagnostic output** from `eval_local.py` includes 10 sections per model:

1. Overall summary
2. Mean scores by subtype
3. First-action distribution
4. First-action confusion vs optimal
5. Final-action confusion vs optimal
6. Mean scores by `verify_effect`
7. Mean scores by `hint_effect`
8. Mean scores by `uncertainty_operator`
9. First-action rate by operator (normalized crosstab)
10. Final-action rate by operator (normalized crosstab)

The model must respond in the following four-line format on each turn:

```
ACTION: <answer|ask_hint|verify|abstain>
ANSWER: <text or NULL>
CONFIDENCE: <0.0–1.0>
RATIONALE: <one sentence>
```

Malformed responses trigger an automatic repair prompt before the turn is scored.

---

## Release Gates

**Degenerate policy gate** — verifies that no fixed-behavior baseline exceeds its score ceiling. Run before publishing a new dataset version:

```bash
# Regenerate baseline scores on the current dataset
python scripts/eval_degenerate_policies.py \
    --data data/mc_intervene_policy_v2_1/mc_intervene_policy_v2_1.csv \
    --out outputs/v2_dev_degenerate_policies.csv

# Check all ceilings
python scripts/check_degenerate_thresholds.py
```

Expected output (exit 0):

```
  STATUS    SCORE  CEILING  POLICY
  ------  -------  -------  ------
  PASS     0.3953     0.40  always_abstain ✓
  PASS     0.3744     0.45  always_answer_no ✓
  PASS     0.4128     0.45  always_answer_yes ✓
  PASS     0.3321     0.40  ask_hint_then_abstain ✓
  PASS     0.4302     0.45  verify_then_abstain ✓
  PASS     0.5114     0.55  verify_then_answer ✓
```

**Resolve-hint audit** — spot-checks that hint payloads are operationally decisive:

```bash
python scripts/audit_resolve_hint_cases.py \
    --data data/mc_intervene_policy_v2_1/mc_intervene_policy_v2_1.csv \
    --n 20
```

---

## Project Structure

```
metacognition_intervene/
├── pyproject.toml
├── data/
│   ├── mc_intervene_dataset_v1/        # v1 arithmetic dataset (400 rows)
│   └── mc_intervene_policy_v2_1/       # v2 policy dataset (900 rows) ← current
├── outputs/
│   └── v2_dev_degenerate_policies.csv  # degenerate baseline scores (release gate input)
├── scripts/
│   ├── eval_local.py                   # Evaluation entry point (10-section diagnostics)
│   ├── eval_degenerate_policies.py     # Score fixed-behavior baselines
│   ├── check_degenerate_thresholds.py  # Release gate (exits 1 if ceiling breached)
│   ├── audit_resolve_hint_cases.py     # Spot-check resolve-hint payload quality
│   └── validate_dataset.py             # CLI wrapper for validate_dataset
└── src/
    └── mc_intervene/
        ├── schema.py                   # Pydantic models (MetaAction, EpisodeResult)
        ├── scoring.py                  # Scoring engine (v1 + v2 formulas, caps)
        ├── eval_local.py               # evaluate_dataframe / summarize_results
        ├── local_model.py              # Ollama interface and response parser
        ├── export.py                   # CSV + metadata export
        ├── worlds/
        │   └── policy_world.py         # PolicyWorld dataclass + world sampler
        ├── renderers/
        │   └── policy_renderers.py     # Four surface renderings per world
        ├── operators/
        │   └── policy_uncertainty.py   # 15 uncertainty operators
        ├── interventions/
        │   └── policy_interventions.py # Hint/verify payload builder + optimal policy
        ├── generators/
        │   ├── policy_v2.py            # v2 bundle generator (9 rows/bundle)
        │   ├── builder.py              # v1 bundle assembly
        │   ├── direct.py
        │   ├── missing.py
        │   ├── trap.py
        │   └── irrecoverable.py
        └── validation/
            └── dataset_validation.py   # Schema, payload, distribution, operator-policy checks
```
