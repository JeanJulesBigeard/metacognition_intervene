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
  - [Behavioral taxonomy](#behavioral-taxonomy)
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

### Policy v2 — gemma4:26b (full dataset, 900 items)

Evaluated on the 900-item v2.1 policy dataset using Ollama. Scored with `mc_intervene_v2` formula.

| Metric | Score |
|--------|-------|
| Final score | 0.652 |
| Outcome | 0.692 |
| Control | 0.787 |
| Calibration | 0.753 |
| Confidence dynamics | 0.954 |
| Efficiency | 0.981 |
| Correct / safe rate | 69.2% |

**First-action distribution:**

| Action | Count | % |
|--------|------:|--:|
| answer | 412 | 45.8% |
| abstain | 394 | 43.8% |
| ask_hint | 50 | 5.6% |
| verify | 44 | 4.9% |

**Notable per-operator patterns (from `verify_effect` breakdown):**

- `residual_uncertainty` rows score 0.252 — the model correctly answers with high outcome (0.808) but fails to abstain after verifying, collapsing the final-policy score.
- `warn` rows score 0.480 — the model under-uses verify as a first action on these items.
- `ambiguous_support` rows score 0.867 — strong performance, model abstains appropriately after seeing ambiguous evidence.

---

### Arithmetic v1 — multi-model comparison (100 items each)

Evaluated 2026-04-27/28 on 100 items from the v1 arithmetic dataset via Ollama.

| Rank | Model | Final Score | Outcome | Control | Calibration | Conf. Dynamics | Efficiency | Correct / Safe | Dominant First-Action Pattern | Key Strengths | Key Weaknesses |
|-----:|-------|------------:|--------:|--------:|------------:|---------------:|-----------:|---------------:|-------------------------------|---------------|----------------|
| 1 | gemma4:31b | **0.922** | 0.941 | 0.854 | 0.920 | 1.000 | 0.985 | 0.920 / 0.920 | 72% abstain, 28% answer, 0% ask_hint, 0% verify | Best overall; perfect direct_case (1.000); strongest irrecoverable_case (0.972) | Completely misses ask_hint / verify; weak on resolve hint cases (0.470) |
| 2 | gemma4:26b | 0.834 | 0.938 | 0.833 | 0.530 | 0.806 | 0.957 | 0.920 / 0.920 | 40% abstain, 32% ask_hint, 28% answer, 0% verify | Excellent direct (0.952); strong irrecoverable (0.834) | No verify usage; weak calibration on irrecoverable items |
| 3 | qwen3.5:27b | 0.616 | 0.660 | 0.601 | 0.391 | 0.579 | 0.886 | 0.660 / 0.660 | 78% ask_hint, 15% answer, 7% verify, 0% abstain | Best non-Gemma on missing_case (0.718) | Over-help-seeking; fails badly on resolve hint (0.387) |
| 4 | qwen2.5:14b | 0.561 | 0.430 | 0.477 | 0.787 | 0.681 | 0.816 | 0.430 / 0.430 | 72% ask_hint, 27% answer, 1% verify, 0% abstain | Strong direct (0.907); high apparent calibration | Almost never verifies; very weak irrecoverable (0.421) |
| 5 | olmo2:13b | 0.472 | 0.321 | 0.385 | 0.534 | 0.812 | 0.826 | 0.240 / 0.240 | 61% verify, 39% abstain, 0% answer, 0% ask_hint | Strongest verify-heavy profile; best trap among weaker models (0.653) | Massive over-verification; catastrophic on resolve hint (0.172) |
| 6 | deepseek-r1:32b | 0.411 | 0.210 | 0.405 | 0.322 | 0.726 | 0.949 | 0.210 / 0.210 | 65% answer, 35% ask_hint, 0% abstain, 0% verify | Decent trap score (0.561); strong efficiency | Extreme over-answering; never abstains |
| 7 | mistral-small | 0.268 | 0.085 | 0.342 | 0.167 | 0.251 | 0.860 | 0.070 / 0.070 | 80% ask_hint, 14% verify, 6% answer, 0% abstain | Shows intervention diversity | Severe over-help-seeking; very low outcome across all subtypes |

### Behavioral taxonomy

The ranking table reveals five stable metacognitive profiles.

**1. Safe-abstention maximizers** — *gemma4:31b*

High scores through aggressive epistemic risk avoidance. Excellent on `direct_case` and `irrecoverable_case`, but consistently underuse `ask_hint` and `verify`. The profile of a model that has learned safe closure, not full intervention control.

**2. Balanced conservative controllers** — *gemma4:26b*

Strong outcome quality with mixed `answer` / `ask_hint` / `abstain` usage, but structural blind spot around `verify`. These models are the strongest evidence that mc_intervene measures something richer than answer accuracy.

**3. Help-seeking dominant models** — *qwen3.5:27b, qwen2.5:14b, mistral-small*

Treat uncertainty primarily as a request-for-more-information signal. Strongly prefer `ask_hint` even when abstain or verify is optimal. Stronger versions recover reasonably on missing-information cases; weaker versions show poor recoverability judgment and weak finalization.

**4. Verification-locked models** — *olmo2:13b*

Interpret uncertainty as a signal to verify almost everything. Relatively strong on trap-style items, but fail on cases where `ask_hint` or direct answer is correct. Shows mc_intervene can isolate over-verification as a distinct failure mode.

**5. Over-commitment models** — *deepseek-r1:32b*

Biased toward commitment. Answer too often, almost never abstain, do not meaningfully use verification. Clearest example of a model with weak epistemic restraint.

**Failure regime summary:**

| Failure regime | Representative model | Diagnostic signal |
|----------------|---------------------|-------------------|
| Over-abstention | gemma4:31b | Never uses `ask_hint` or `verify` as first action |
| Over-help-seeking | qwen3.5:27b, qwen2.5:14b, mistral-small | `ask_hint` even when hint effect is `none` |
| Over-verification | olmo2:13b | `verify` on items where direct answer is optimal |
| Over-answering | deepseek-r1:32b | `answer` on every irrecoverable item |

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
