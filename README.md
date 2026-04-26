# mc_intervene

**mc_intervene** is a metacognitive benchmark that evaluates whether a language model can choose the right intervention under uncertainty: answer, ask for a hint, verify, or abstain. Instead of rewarding only final-answer accuracy, it measures whether the model can regulate its own problem-solving process and adapt its behavior when evidence is incomplete, misleading, or only partially helpful.

The benchmark is built from procedurally generated, paired scenarios with similar surface structure but different hidden epistemic states. This forces models to infer whether uncertainty is recoverable, whether verification is worthwhile, and whether commitment is justified. Each item is scored on five dimensions: outcome quality, control quality, calibration, confidence dynamics, and efficiency. Together, these metrics make mc_intervene a process-level evaluation of metacognitive control rather than a standard reasoning or QA benchmark.

---

## Table of Contents

- [Concepts](#concepts)
- [Scenario Types](#scenario-types)
- [Scoring](#scoring)
- [Installation](#installation)
- [Generating a Dataset](#generating-a-dataset)
- [Evaluating a Model](#evaluating-a-model)
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

Items are grouped into **bundles** of four (one per scenario type). Within a bundle, problems share surface structure but differ in hidden state. This pairing design controls for task difficulty and isolates metacognitive skill from domain knowledge.

---

## Scenario Types

### Direct (`direct_case`)

Arithmetic problems where the information provided is complete but the appropriate level of caution varies.

| Variant | Solvability | Verify Effect | Optimal First Action |
|---------|-------------|---------------|----------------------|
| `clean_exact` | solvable_direct | confirm | answer |
| `tempt_verify` | solvable_direct | weak_confirm | answer or verify |
| `cautious_wording` | solvable_direct | warn | answer or verify |
| `precision_mismatch` | irrecoverable | insufficient | abstain |
| `rounded_report` | irrecoverable | residual_uncertainty | abstain |

### Missing (`missing_case`)

Problems where a key piece of information is absent. The value of asking for a hint depends on what the hint can actually provide.

| Hint Effect | What the hint provides | Optimal policy |
|-------------|----------------------|----------------|
| `resolve` | The missing value exactly | ask_hint → answer |
| `partial` | A narrowed range, not a definitive value | ask_hint → abstain |
| `none` | Nothing useful | abstain |

### Trap (`trap_case`)

Superficially clear problems that contain a misleading element (e.g. digit reversal). Verification exposes whether the apparent answer is safe to commit to.

| Verify Effect | Optimal policy |
|---------------|----------------|
| `confirm` / `weak_confirm` | verify → answer |
| `warn` | verify → answer (with caution) |
| `ambiguous_support` / `residual_uncertainty` | verify → abstain |

### Irrecoverable (`irrecoverable_case`)

Problems where the ground truth cannot be determined from the available information alone. Some variants look recoverable but are not; others can be resolved only via hint.

| Variant | Hint Effect | Optimal policy |
|---------|-------------|----------------|
| `true_abstain` | none | abstain |
| `hint_resolves` | resolve | ask_hint → answer |
| `hint_partial` | partial | ask_hint → abstain |
| `verify_warn_only` | none | abstain |
| `deceptive_recoverable_looking` | partial | ask_hint → abstain |
| `near_threshold_unknown` | partial | ask_hint → abstain |

---

## Scoring

Each episode is scored on five dimensions. The final score is a weighted sum.

```
final_score = 0.35 × outcome
            + 0.30 × control
            + 0.15 × calibration
            + 0.10 × confidence_dynamics
            + 0.10 × efficiency
```

### Outcome (35%)

Was the model's final commitment correct?

- Correct answer on a solvable item → 1.0
- Abstain on an irrecoverable item → 1.0
- Wrong answer → 0.0
- Answer on an irrecoverable item → 0.0

### Control (30%)

Did the model follow a sound decision process?

- **First action** (45% of control): does it match the optimal or acceptable first action?
- **Transition** (25% of control): given the first action's result, was the transition appropriate?
- **Final policy** (30% of control): does the final action match the optimal policy?

### Calibration (15%)

Is the model's stated confidence warranted?

Measured as `1 - (confidence - correctness)²` on the final action. A model that says 0.9 confidence and is right scores near 1.0; one that says 0.9 and is wrong scores near 0.19.

### Confidence Dynamics (10%)

Does the model update its confidence appropriately after receiving feedback?

- After a resolving hint: confidence should rise.
- After a partial hint: confidence should fall or stay low.
- After a confirming verification: confidence should rise.
- After a warning verification: confidence should fall.

### Efficiency (10%)

Are information-seeking actions actually necessary?

Penalties:
- Unnecessary hint: −0.15
- Unnecessary verify: −0.12
- Answering when verification was warranted: −0.10
- Repeated information-seeking in one episode: −0.20

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

**CLI:**

```bash
mc-intervene --n-bundles 100 --seed 67 --out-dir data/mc_intervene_dataset_v1
```

**Python:**

```python
from mc_intervene.generators.builder import build_mc_intervene_df
from mc_intervene.export import export_dataset

df = build_mc_intervene_df(n_bundles=100, seed=67)
export_dataset(df, out_dir="data/mc_intervene_dataset_v1")
```

Each bundle produces four items (one per scenario type), so 100 bundles → 400 rows. The export writes `mc_intervene_eval.csv` and `metadata.json` to the output directory.

A pre-generated dataset (200 bundles, 800 rows) is included at [data/mc_intervene_dataset_v1/](data/mc_intervene_dataset_v1/).

---

## Evaluating a Model

**Script (Ollama):**

```bash
python scripts/eval_local.py \
    --data data/mc_intervene_dataset_v1/mc_intervene_eval.csv \
    --model llama3.2 \
    --provider ollama \
    --base-url http://localhost:11434 \
    --limit 50
```

**Python API:**

```python
from mc_intervene.local_model import OllamaPolicy
from mc_intervene.scoring import score_mc_intervene_v6_episode
from mc_intervene.eval_local import evaluate_dataframe, summarize_results
import pandas as pd

df = pd.read_csv("data/mc_intervene_dataset_v1/mc_intervene_eval.csv")
policy = OllamaPolicy(model="llama3.2", base_url="http://localhost:11434")

results = evaluate_dataframe(df, policy, score_mc_intervene_v6_episode)
print(summarize_results(results))

# Break down by scenario type
print(results.groupby("subtype")[["final_score", "outcome_score", "control_score"]].mean())
```

The model must respond in the following four-line format on each turn:

```
ACTION: <answer|ask_hint|verify|abstain>
ANSWER: <text or NULL>
CONFIDENCE: <0.0–1.0>
RATIONALE: <one sentence>
```

Malformed responses trigger an automatic repair prompt before the turn is scored.

---

## Project Structure

```
metacognition_intervene/
├── pyproject.toml
├── data/
│   └── mc_intervene_dataset_v1/
│       ├── mc_intervene_eval.csv   # 800-row pre-generated dataset
│       └── metadata.json
├── scripts/
│   └── eval_local.py               # Evaluation entry point
└── src/
    └── mc_intervene/
        ├── cli.py                  # mc-intervene CLI
        ├── schema.py               # Pydantic data models (ItemRow, MetaAction, EpisodeResult)
        ├── policy.py               # Optimal policy derivation
        ├── scoring.py              # Five-dimension scoring (v6)
        ├── local_model.py          # Ollama interface and response parser
        ├── eval_local.py           # evaluate_dataframe / summarize_results
        ├── export.py               # CSV + metadata export
        └── generators/
            ├── base.py             # Abstract generator
            ├── builder.py          # Bundle assembly
            ├── direct.py           # Direct case generator
            ├── missing.py          # Missing information generator
            ├── trap.py             # Trap / misleading case generator
            └── irrecoverable.py    # Irrecoverable case generator
```
