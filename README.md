# mc_intervene

> **mc_intervene v2.1: A Counterfactual Benchmark for Metacognitive Intervention Control**
>
> *Evaluating whether language models can choose when to answer, ask for missing information, verify evidence, or abstain under structured uncertainty.*

---

## \[METACOGNITION\] When Should an AI Model Answer, Ask, Verify, or Abstain?

*A counterfactual benchmark for metacognitive intervention control — originally published on [Substack](https://doublej37.substack.com/p/when-should-an-ai-model-answer-ask), May 09, 2026.*

---

A model is given this case:

> Project Helix completed the milestone review 8 days before the deadline. The required form was submitted. Project Helix does not have priority status. The policy threshold for the deployment credit is not disclosed.
>
> Does Project Helix qualify for the deployment credit?

Most benchmarks would ask: did the model answer correctly?

I wanted to ask something slightly different:

> **Should the model answer at all?**

Maybe it should answer. Maybe it should ask for the missing threshold. Maybe it should verify an inconsistent record. Maybe it should abstain because the missing information cannot be recovered.

That distinction is the motivation behind `mc_intervene`: a benchmark for evaluating whether language models choose the right **epistemic action** before committing to an answer.

The four actions are deliberately simple:

| Action | Meaning |
|--------|---------|
| `answer` | Commit to a final answer |
| `ask_hint` | Request a hint that may resolve missing information |
| `verify` | Check a supporting document that may confirm or contradict the current path |
| `abstain` | Decline to answer because the problem is epistemically unresolvable |

The capability being tested is not generic QA. It is **metacognitive intervention control**: can the model identify the source of uncertainty and choose the action with the highest epistemic value?

### Why final-answer accuracy is not enough

A model can get the final answer right for the wrong reason.

It can guess. It can over-abstain. It can always ask for hints. It can always verify. It can answer using spurious priors. Many of these policies will look reasonable under a final-accuracy metric, especially if the dataset distribution happens to reward them.

This matters because frontier systems are increasingly expected to operate in settings where the right move is not always "answer now." In many realistic workflows, the model should first decide whether it has enough information, whether it should inspect evidence, whether a missing variable is recoverable, or whether no justified answer is possible.

So I built a benchmark where the latent world is known to the evaluator, but the model only sees a rendered, partially degraded view of that world.

The pipeline is:

```
PolicyWorld → rendered public view → uncertainty operator → hint / verification payload → optimal policy → model action → scoring
```

Each hidden world can generate multiple counterfactual variants. The factual substrate stays fixed, but the visible epistemic state changes.

For example, the same underlying case can be rendered as:

- A **short narrative** (prose description of entity and facts)
- A **policy excerpt** (formal policy document + compliance record)
- An **evidence bundle** (structured field-value list)
- A **table record** (tabular row)

This counterfactual structure is the key design choice. It prevents the benchmark from becoming a set of surface-pattern prompts and instead asks whether the model tracks the value of an intervention.

### Intervention Value Alignment

The central metric is **Intervention Value Alignment**, or IVA.

Outcome scoring asks:

> Did the model end up right?

IVA asks:

> Did the model choose the right epistemic move before ending up right?

A model receives high IVA when its first action matches the intervention that actually has epistemic value in that case.

This lets the benchmark distinguish:

- `right answer, right process`
- `right answer, wrong process`
- `wrong answer, reasonable process`
- `wrong answer, wrong process`

That distinction is the core point of the benchmark.

### The v2.1 dataset

The current version is `mc_intervene_policy_v2.1`.

It contains 900 rows across 14 uncertainty operators, grouped into 100 bundles of 9 items each. Each bundle shares the same underlying world; the 9 items apply different operators to vary the epistemic state the model sees.

The operators are grouped by the optimal first action they are designed to test:

| Group | Operators | Optimal first action |
|-------|-----------|---------------------|
| **Answer** | `none`, `direct_answerable_hard`, `answerable_weak_verify` | `answer` |
| **Ask hint** | `hide_threshold`, `hint_resolves_missing_field`, `hint_resolves_exception` | `ask_hint` |
| **Verify** | `hide_exception`, `inject_conflict`, `inject_policy_caveat`, `inject_incomplete_record`, `verify_residual_uncertainty` | `verify` |
| **Abstain** | `make_rule_ambiguous`, `inject_unverifiable_requirement`, `irrecoverable_missing_record` | `abstain` |

The dataset is synthetic, but the structure is meant to capture a real pattern: the difference between knowing an answer and knowing whether an answer is justified.

### Degenerate policy gates

A benchmark like this is not useful if trivial policies can win.

So before evaluating models, I added degenerate baselines. The release gate requires blind policies to stay below fixed ceilings:

| Policy | Ceiling | Phase 8 result |
|--------|--------:|:--------------|
| `always_abstain` | 0.42 | PASS |
| `always_answer_yes` | 0.45 | PASS |
| `always_answer_no` | 0.45 | PASS |
| `ask_hint_then_abstain` | 0.40 | PASS |
| `verify_then_abstain` | 0.45 | PASS |
| `verify_then_answer` | 0.55 | PASS |

This was important. Earlier versions of the benchmark accidentally rewarded `verify_then_answer` too strongly because too many rows were verify-optimal. Rebalancing the dataset and adding IVA made the benchmark much harder to game.

### Local model results

I evaluated seven Ollama-local models on the 900-row v2.1 set:

| Rank | Model | full\_with\_iva | no\_iva | Δ | outcome | IVA | Behavior class |
|-----:|-------|:--------------:|:-------:|:---:|--------:|----:|----------------|
| 1 | gemma4:31b | **0.784** | 0.817 | +0.033 | 0.799 | 0.699 | strong\_adaptive\_intervention\_averse |
| 2 | gemma4:26b | 0.708 | 0.744 | +0.036 | 0.692 | 0.613 | adaptive\_conservative |
| 3 | qwen3.5:27b | 0.688 | 0.750 | +0.062 | 0.748 | 0.533 | high\_outcome\_help\_seeker |
| 4 | olmo2:13b | 0.518 | 0.525 | +0.007 | 0.356 | 0.488 | conservative\_closure |
| 5 | mistral-small | 0.510 | 0.526 | +0.016 | 0.430 | 0.455 | mixed\_low\_control |
| 6 | qwen2.5:14b | 0.507 | 0.547 | +0.040 | 0.460 | 0.400 | help\_seeking\_collapse |
| 7 | deepseek-r1:32b | 0.436 | **0.403** | **−0.033** | 0.287 | 0.489 | over\_answering\_weak\_final\_policy |

The strongest local model is `gemma4:31b`. It beats all blind degenerate policies and remains well below oracle — the range I wanted: the task is neither trivial nor impossible.

But the more interesting result is not the ranking. It is the behaviour taxonomy.

### Behavioral signatures

**gemma4:31b — strong adaptive, but intervention-averse**

`gemma4:31b` is the best local model in this run. It does well on direct-answer and clear-abstention cases. It also avoids many degenerate traps. But it still underuses active interventions. The pattern: good final judgment, strong answer/abstain separation, weak ask\_hint/verify selection. The model often knows whether to commit or refrain, but does not reliably choose the epistemic action that would make the commitment justified.

**qwen3.5:27b — high-outcome help-seeker**

`qwen3.5:27b` has a high outcome score but a lower IVA score. It often reaches the right final answer while choosing weaker first actions — in particular, it overuses `ask_hint`. Under no-IVA scoring it overtakes `gemma4:26b`; with IVA it stays behind. That is exactly why IVA matters: without it, high final-answer accuracy can hide weak metacognitive control.

**olmo2:13b — conservative closure**

`olmo2:13b` tends to verify or abstain, then final-abstain. It is safe in some cases but not adaptive. A classic conservative failure mode: the model avoids risk but also avoids solving answerable cases.

**qwen2.5:14b — help-seeking collapse**

`qwen2.5:14b` often maps uncertainty to `ask_hint`, even when the correct action is `verify`, `answer`, or `abstain`. The inverse of over-abstention: the model treats missing confidence as a request-for-help problem, even when the help channel has low value.

**deepseek-r1:32b — over-answering**

`deepseek-r1:32b` is weak on this benchmark because it over-commits. It answers in cases where the correct final policy is abstention, especially on irrecoverable or ambiguous records — the failure mode one would worry about in settings where unjustified commitment is costly.

### The IVA ablation

The IVA ablation is one of the strongest findings.

I recomputed model scores with the same model trajectories but removed the IVA component from the top-line score. The key result:

> Removing IVA promotes high-outcome but epistemically misaligned models.

With IVA, `gemma4:26b` remains ahead of `qwen3.5:27b` despite Qwen's higher outcome score. Without IVA, `qwen3.5:27b` overtakes it. That is the benchmark's central empirical argument: outcome scoring alone partially collapses final-answer success and epistemic action quality.

IVA is not just a penalty term. It is a trajectory-quality signal. It answers a different question:

> Did the model choose the right way to become justified?

### Operator-level findings

**`verify_residual_uncertainty` is universally hard.** All models score poorly on cases where verification is the correct first action but the verification result still leaves residual uncertainty. Many models can abstain. Many models can verify. But they struggle to do both in the correct sequence.

**`hide_threshold` is where Qwen beats Gemma.** On threshold-hidden cases, Qwen models perform relatively well because their help-seeking bias is actually useful. Gemma models are stronger overall but more intervention-averse here. The benchmark does not merely rank models monotonically — it identifies local capability inversions.

**`inject_conflict` is a Gemma strength.** Gemma models are notably stronger on conflicting-evidence cases. They are more likely to handle the record conflict appropriately, while Qwen and Mistral often ask for hints or fail to verify.

**DeepSeek over-answers non-answerable cases.** On ambiguous or irrecoverable cases, DeepSeek-style over-commitment leads to low scores — a qualitatively different failure mode from Qwen's help-seeking or OLMo's conservative closure.

### What this benchmark is, and is not

This is not a claim that synthetic policy eligibility is the only domain that matters.

It is a controlled domain for isolating a narrow capability:

> Can a model choose the epistemic action with the highest expected value?

The current benchmark is a prototype. Limitations:

- The domain is synthetic.
- The examples are policy-style eligibility tasks.
- The current results are local Ollama model results, not hosted frontier API results.
- Some positive-control hint cases are too easy.
- There is no human baseline yet.

But the current results are already enough to show that this evaluation slice is meaningful. Models do not just differ in final accuracy. They differ in their **policies for handling uncertainty**.

### Why I think this matters

As models become more agentic, the relevant question is often not:

> Can the model answer?

but:

> Does the model know what kind of epistemic position it is in?

A good model should know when it has enough evidence, when it should request missing information, when it should verify a source, and when no justified answer is possible. That is a different capability from standard question answering. `mc_intervene` is an attempt to make that capability measurable.

The current version shows:

1. Strong models are better at final answer/abstain decisions.
2. Even strong models underuse high-value interventions.
3. Different models have stable metacognitive failure modes.
4. IVA changes the ranking in exactly the cases where outcome scoring hides weak epistemic control.
5. Operator-level diagnostics reveal targeted weaknesses, not just scalar scores.

The benchmark does not just say "model A is better than model B." It says *how* they manage uncertainty differently.

### What comes next

1. Expand beyond policy eligibility.
2. Add more multi-step evidence acquisition.
3. Add adversarial distractors.
4. Run hosted frontier models.
5. Add human baselines.
6. Publish a dataset card and stronger reproducibility package.
7. Test whether training on explicit epistemic-action supervision improves IVA without overfitting the final answer.

---

## TL;DR

**The problem.** Standard QA benchmarks reward final-answer accuracy, but say nothing about *how* a model arrived at its answer. A model that guesses correctly and a model that reasons correctly look identical. mc_intervene measures the decision process itself: given a prompt whose solvability is uncertain, did the model choose the right epistemic action before committing?

**The setup.** Each item presents a policy eligibility scenario with a hidden structured world state. The model must pick one of four first actions — `answer`, `ask_hint`, `verify`, or `abstain` — and optionally a second action after receiving feedback. Optimal behavior depends on the hidden state: whether a key threshold is redacted, whether an administrative conflict exists, whether the missing information is actually recoverable.

**A concrete example.** A short-narrative item under the `hide_threshold` operator looks like this:

> *Project Helix completed the milestone review 8 days before the deadline. The required form was submitted. Project Helix does not have priority status. The policy threshold for the deployment credit is not disclosed.*
>
> Does Project Helix qualify for the deployment credit?

The model cannot answer from the prompt alone — the threshold is hidden. The optimal first action is `ask_hint`. The hint payload reveals the base threshold is 7 days, resolving the question to "yes". A model that answers directly, or abstains, is making the wrong epistemic choice even if it happens to guess correctly.

**How items are generated.** A `PolicyWorld` is sampled with randomised days-early, threshold, priority status, and form requirements. One of 14 **uncertainty operators** is applied to inject a specific epistemic gap (hidden threshold, injected conflict, ambiguous policy rule, unverifiable requirement, etc.). The world is rendered in four surface formats (short narrative, policy excerpt, evidence bundle, table record). Each bundle of 9 items shares the same world but spans all four epistemic actions: 2 answer-optimal, 2 ask-hint-optimal, 3 verify-optimal, 2 abstain-optimal. 100 bundles → 900 rows.

**Key findings** (7 local models, 900 items, v2.1 dataset):

- The strongest local model, gemma4:31b, scores **0.784** (ablation score) / **0.741** (capped runtime score) — well above the best blind degenerate baseline (`verify_then_answer` at **0.518**). The top three models clear that bar; the bottom four fall within the degenerate-policy band, which is itself diagnostically useful.
- Models have **stable metacognitive signatures**: each has a characteristic first-action distribution that is largely independent of what the item requires. gemma4:31b answers or abstains 88% of the time; qwen2.5:14b asks for a hint 67% of the time; deepseek-r1:32b answers on 99% of final actions.
- Final-answer accuracy and intervention control **diverge**: qwen3.5:27b has the second-best outcome score (0.748) but ranks third overall because it defaults to `ask_hint` even when `verify` or direct answer is correct.
- **Models are not primarily failing because they cannot compute the answer.** They fail because they do not reliably choose the epistemic action that would make the answer justified. That is the target capability of this benchmark.

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
  - [IVA ablation](#iva-ablation)
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

Each item is transformed by one of 14 **uncertainty operators** that inject a specific epistemic gap into the rendered scenario. Operators are grouped by the optimal first action they induce:

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

100 bundles → **900 rows**. Pre-generated dataset: [`data/mc_intervene_policy_v2_1_dev/`](data/mc_intervene_policy_v2_1_dev/). A 20-row sample is committed at [`data/examples/mc_intervene_policy_v2_sample_20.csv`](data/examples/mc_intervene_policy_v2_sample_20.csv).

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

Items with `task_family = "mc_intervene_v2"` use a formula that elevates **intervention value alignment** (IVA — did the model choose the epistemically correct first action?):

```
final_score = 0.35 × outcome
            + 0.30 × intervention_value_alignment
            + 0.20 × control
            + 0.10 × calibration
            + 0.05 × efficiency
```

Score ceilings cap the final score for systematically wrong trajectory patterns (e.g., abstaining when an intervention was available: cap 0.30; answering when abstain was optimal: cap 0.35). Full IVA scoring table, ceiling table, and ablation formula: [docs/SCORING.md](docs/SCORING.md).

---

## Dataset Validation

Full dataset documentation — schema, operators, bundle structure, limitations, intended and not-intended use — is in the [dataset card](data/mc_intervene_policy_v2_1_dev/DATASET_CARD.md).

The `validate_dataset` function checks structural integrity, payload completeness, action-label consistency, and operator-to-policy consistency. It is run automatically during dataset generation.

```python
from mc_intervene.validation import validate_dataset
import pandas as pd

df = pd.read_csv("data/mc_intervene_policy_v2_1_dev/mc_intervene_policy_v2.csv")
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

Full 7-model evaluation on the 900-item v2.1 policy dataset via Ollama. Oracle scores 0.998; best blind degenerate baseline (`verify_then_answer`) scores 0.518. The top three models clear that bar; the bottom four do not, placing them in the same performance tier as the better degenerate heuristics.

Scores are recomputed from per-item component columns using the v2.1_full formula without trajectory caps (`full_with_iva`), enabling direct comparison with the IVA ablation. The `no_iva` column uses the redistributed formula (outcome×0.50, control×0.30, calibration×0.15, efficiency×0.05).

> **Note on score families.** Two score values appear in this README. *Operational scores* (capped) are produced by the full scorer including per-trajectory behaviour ceilings; these are used by the release gate and in raw `.txt` eval outputs. *Ablation scores* (uncapped) are recomputed from per-item component columns so that the only varying factor is the formula. Ablation scores are higher on average (~+0.03). The leaderboard table above uses ablation scores to keep the IVA comparison consistent.

| Rank | Model | full\_with\_iva | no\_iva | Δ | outcome | IVA | correct% | Behavior class |
|-----:|-------|:--------------:|:-------:|:---:|--------:|----:|--------:|----------------|
| 1 | gemma4:31b | **0.784** | 0.817 | +0.033 | 0.799 | 0.699 | 79.9% | strong\_adaptive\_intervention\_averse |
| 2 | gemma4:26b | 0.708 | 0.744 | +0.036 | 0.692 | 0.613 | 69.2% | adaptive\_conservative |
| 3 | qwen3.5:27b | 0.688 | 0.750 | +0.062 | 0.748 | 0.533 | 74.8% | high\_outcome\_help\_seeker |
| 4 | olmo2:13b | 0.518 | 0.525 | +0.007 | 0.356 | 0.488 | 35.6% | conservative\_closure |
| 5 | mistral-small | 0.510 | 0.526 | +0.016 | 0.430 | 0.455 | 43.0% | mixed\_low\_control |
| 6 | qwen2.5:14b | 0.507 | 0.547 | +0.040 | 0.460 | 0.400 | 46.0% | help\_seeking\_collapse |
| 7 | deepseek-r1:32b | 0.436 | 0.403 | **−0.033** | 0.287 | 0.489 | 28.7% | over\_answering\_weak\_final\_policy |

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

### IVA ablation

We ablated the intervention-value-alignment component while holding the dataset, model trajectories, and parser fixed. The scoring formula changes; nothing else does. Scores are recomputed from per-item component columns without trajectory caps; the resulting values are slightly higher than the capped leaderboard scores but enable clean formula comparison across models and degenerate policies.

Two formulas:

| | outcome | IVA | control | calibration | efficiency |
|---|---|---|---|---|---|
| **v2\_1\_full** | 0.35 | **0.30** | 0.20 | 0.10 | 0.05 |
| **v2\_1\_no\_iva** | 0.50 | — | 0.30 | 0.15 | 0.05 |

#### Model-level: rank shifts under no-IVA scoring

| Rank (full) | Model | full\_with\_iva | no\_iva | Δ | Rank (no-IVA) | Shift |
|:-----------:|-------|:--------------:|:-------:|:---:|:-------------:|:-----:|
| 1 | gemma4:31b | **0.784** | 0.817 | +0.033 | 1 | 0 |
| 2 | gemma4:26b | 0.708 | 0.744 | +0.036 | 3 | **−1** |
| 3 | qwen3.5:27b | 0.688 | **0.750** | +0.062 | 2 | **+1** |
| 4 | olmo2:13b | 0.518 | 0.525 | +0.007 | 6 | **−2** |
| 5 | mistral-small | 0.510 | 0.526 | +0.016 | 5 | 0 |
| 6 | qwen2.5:14b | 0.507 | 0.547 | +0.040 | 4 | **+2** |
| 7 | deepseek-r1:32b | 0.436 | **0.403** | **−0.033** | 7 | 0 |

Three rank changes warrant explanation:

**qwen3.5:27b (+1):** High outcome (0.748) but lower IVA (0.533). Removing IVA and promoting outcome to 0.50 weight gives qwen3.5 more credit for its correct final decisions and less penalty for its hint-heavy trajectory. It overtakes gemma4:26b in the no-IVA ranking.

**gemma4:26b (−1):** Gemma's trajectory is more epistemically aligned (IVA=0.613) than qwen3.5's. IVA is rewarding this. Without IVA, the lower outcome (0.692 vs 0.748) pulls gemma4:26b below qwen3.5.

**deepseek-r1:32b (unique: Δ = −0.033):** deepseek is the only model that falls without IVA. Its IVA (0.489) is disproportionately high relative to its outcome (0.287). Removing IVA lets the very poor outcome dominate at 0.50 weight. This reveals that deepseek chooses appropriate *first actions* but then ignores their signal and answers regardless — correct epistemic intent, no epistemic follow-through.

**IVA preserves the Gemma/Qwen distinction at the trajectory level.** Under full-IVA scoring, gemma4:26b leads qwen3.5:27b (0.708 vs 0.688). Under no-IVA scoring, qwen3.5 overtakes gemma4:26b (0.750 vs 0.744). The 26-point outcome gap between the two is visible to both formulas, but IVA adds the information that Gemma earns that outcome via better epistemic paths.

#### Degenerate-policy ablation: IVA as trajectory-quality discriminator

The degenerate policies make the mechanism transparent. Policies with identical outcome accuracy are separated by IVA because their trajectories differ in epistemic value.

| Policy | outcome | IVA | full\_with\_iva | no\_iva | Δ | Interpretation |
|--------|--------:|----:|:--------------:|:-------:|:---:|----------------|
| oracle | 1.000 | 1.000 | 0.998 | 0.997 | −0.001 | Optimal trajectory; should remain near ceiling |
| direct\_gold\_answer | 0.644 | 0.383 | 0.564 | 0.577 | +0.013 | Omniscient cheat: correct outcome, wrong epistemic path |
| verify\_then\_answer | 0.644 | 0.409 | 0.518 | 0.507 | −0.011 | Verify-first, high IVA: falls without IVA |
| always\_answer\_yes | 0.363 | 0.383 | 0.449 | 0.435 | −0.014 | Blind positive answer |
| ask\_hint\_then\_answer | 0.644 | 0.138 | 0.442 | 0.450 | +0.008 | Same outcome as verify\_then\_answer; low IVA: rises without IVA |
| verify\_then\_abstain | 0.356 | 0.409 | 0.424 | 0.406 | −0.018 | Verify-first: falls without IVA |
| always\_answer\_no | 0.281 | 0.383 | 0.414 | 0.395 | −0.020 | Blind negative answer |
| always\_abstain | 0.356 | 0.339 | 0.407 | 0.421 | +0.014 | Conservative; rises without IVA |
| ask\_hint\_then\_abstain | 0.356 | 0.138 | 0.336 | 0.354 | +0.018 | Low-value help-seeking: rises without IVA |

The critical comparison is `verify_then_answer` vs `ask_hint_then_answer`: both achieve outcome 0.644. Their full-IVA scores differ by 0.076 (0.518 vs 0.442). Under no-IVA scoring the gap collapses to 0.057. IVA is rewarding the verify-first trajectory because verification is epistemically optimal on 33% of the dataset; hint-first is only optimal on 11%.

The sign of Δ tracks IVA score directly: policies with IVA ≥ 0.38 (verify-first, blind-answer) all fall without IVA; policies with IVA = 0.138 (hint-first) both rise. IVA is not simply a degenerate-policy penalty — it distinguishes *among* policies by the quality of their epistemic path, not by whether they are degenerate.

**Artifact references:**  `reports/tables/model_iva_ablation_table.csv` · `reports/tables/degenerate_baseline_table.csv`

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

4. **Degenerate policies are controlled.** The best blind baseline (`verify_then_answer`) scores 0.518. The top three local models exceed it; the bottom four remain in or near the degenerate-policy band. Blind abstention, blind answering, and blind hint-seeking all score below 0.45.

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

**To Do:**

- Hosted/frontier model results (GPT-4o, Claude, Gemini) on v2.1
- Human spot-check of 30–50 generated rows
- Multi-sample evaluation to characterise per-item variance

**Status:** research prototype / v2.1 local-evaluation release. All current results are from local Ollama models; no API-hosted frontier model results are included yet.

---

## Installation

```bash
git clone https://github.com/jeanjulesbigeard/mc_intervene.git
cd mc_intervene
pip install -e .
```

Python 3.10 or later is required. Dependencies: `pandas`, `pydantic`, `pyyaml`.

For local model evaluation, [Ollama](https://ollama.com) must be running. For exact model tags, dataset SHA-256, and full eval commands see [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md).

---

## Generating a Dataset

**Policy v2 (recommended):**

```bash
mc-intervene-policy \
    --n-bundles 100 \
    --seed 67 \
    --out-dir data/mc_intervene_policy_v2_1_dev
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
export_dataset(df, out_dir="data/mc_intervene_policy_v2_1_dev")
```

---

## Evaluating a Model

**Script (Ollama):**

```bash
python scripts/eval_local.py \
    --data data/mc_intervene_policy_v2_1_dev/mc_intervene_policy_v2.csv \
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

df = pd.read_csv("data/mc_intervene_policy_v2_1_dev/mc_intervene_policy_v2.csv")
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
    --data data/mc_intervene_policy_v2_1_dev/mc_intervene_policy_v2.csv \
    --out outputs/v2_dev_degenerate_policies.csv

# Check all ceilings
python scripts/check_degenerate_thresholds.py
```

Expected output (exit 0):

```
  STATUS    SCORE  CEILING  POLICY
  ------  -------  -------  ------
  PASS     0.4070     0.42  always_abstain ✓
  PASS     0.4145     0.45  always_answer_no ✓
  PASS     0.4489     0.45  always_answer_yes ✓
  PASS     0.3364     0.40  ask_hint_then_abstain ✓
  PASS     0.4236     0.45  verify_then_abstain ✓
  PASS     0.5179     0.55  verify_then_answer ✓
```

**Resolve-hint audit** — spot-checks that hint payloads are operationally decisive:

```bash
python scripts/audit_resolve_hint_cases.py \
    --data data/mc_intervene_policy_v2_1_dev/mc_intervene_policy_v2.csv \
    --n 20
```

---

## Project Structure

```
metacognition_intervene/
├── pyproject.toml
├── data/
│   ├── mc_intervene_dataset_v1/        # v1 arithmetic dataset (400 rows)
│   ├── mc_intervene_policy_v2_1_dev/   # v2.1 policy dataset (900 rows) ← current
│   └── examples/                       # 20-row sample (committed)
├── outputs/                            # git-ignored; created on first run
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
        │   └── policy_uncertainty.py   # 14 uncertainty operators
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
├── docs/
│   ├── SCORING.md                                  # Full v1/v2 formula, IVA table, ceilings, score families
│   ├── OPERATORS.md                                # Operator taxonomy, distributions, Phase 8 diagnostics
│   ├── DATASET_CARD.md                             # Quick-reference + pointer to full card in data/
│   └── REPRODUCIBILITY.md                          # Seeds, model tags, commands, SHA-256, release gate
├── reports/
│   ├── phase8_frontier_lab_report.md
│   └── tables/                                     # Committed report CSVs
│       ├── phase8_model_leaderboard.csv
│       ├── degenerate_baseline_table.csv
│       ├── degenerate_iva_ablation_table.csv
│       ├── model_iva_ablation_table.csv
│       ├── operator_scores_by_model.csv
│       ├── operator_first_action_rates_by_model.csv
│       └── operator_final_action_rates_by_model.csv
├── LICENSE
└── CITATION.cff
```
