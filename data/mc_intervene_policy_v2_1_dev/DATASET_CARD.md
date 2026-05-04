# Dataset Card — mc_intervene_policy_v2_1_dev

| Field | Value |
|---|---|
| Name | `mc_intervene_policy_v2_1_dev` |
| File | `mc_intervene_policy_v2.csv` |
| Rows | 900 |
| Bundles | 100 |
| Task family | `mc_intervene_v2` |
| Split | dev |
| SHA-256 | `37e278860fd342f3f16ada41e8888e7dc6063d8ebd9e1d847cf042fd73c31208` |

---

## Task definition

Each item presents a **policy eligibility scenario**: a world description (facts about an entity and its actions) plus a policy document (rules that govern eligibility). The model must decide whether to:

- **answer** — commit to yes/no directly
- **ask_hint** — request a structured hint that surfaces hidden or missing information
- **verify** — check a supporting document that confirms, qualifies, or contradicts the visible record
- **abstain** — refuse to answer because the case is epistemically unresolvable

The correct choice depends on the uncertainty operator applied to the item. Some cases are directly answerable; others have hidden fields, injected conflicts, or missing records that require intervention before a reliable answer is possible.

The benchmark rewards the full epistemic trajectory — not just the final answer. A model that abstains correctly without verifying when verification was available scores lower than one that verifies first and then abstains.

---

## Schema

| Column | Type | Description |
|---|---|---|
| `item_id` | string | Unique item identifier. Format: `policy_world_{id}_{view}_{operator}_{idx}` |
| `world_id` | string | The base world this item was generated from. Items in the same bundle share a world. |
| `paired_item_group` | string | Bundle identifier. All 9 variants of a base world share this key. |
| `task_family` | string | Always `mc_intervene_v2` for this dataset. |
| `domain` | string | Always `policy_eligibility`. |
| `subtype` | string | Always `policy_case`. |
| `variant` | string | The uncertainty operator applied. See **Operators** section. |
| `view_type` | string | Surface rendering: `short_narrative`, `policy_excerpt`, `evidence_bundle`, `table_record`. Balanced 225 per type. |
| `prompt_text` | string | The full prompt shown to the model. Contains world description and yes/no policy question. |
| `ground_truth` | string | The observable ground truth answer (`yes`/`no`). |
| `latent_ground_truth` | string | The true answer given full information (may differ from `ground_truth` when fields are hidden). |
| `epistemic_answerability` | string | `answerable` or `not_answerable`. Ground truth for whether an answer is epistemically justified. |
| `uncertainty_source` | string | Source of uncertainty: `none`, `hidden_field`, `injected_conflict`, `policy_ambiguity`, `missing_record`. |
| `uncertainty_operator` | string | Specific operator applied. See **Operators** section. |
| `recoverability_type` | string | Whether uncertainty is recoverable and by which intervention. See below. |
| `hint_effect` | string | What a hint provides: `none`, `partial`, `resolve`. |
| `verify_effect` | string | What verification provides: `confirm`, `weak_confirm`, `warn`, `ambiguous_support`, `insufficient`, `residual_uncertainty`. |
| `hint_payload` | string | The structured hint text the model receives if it asks for one. |
| `verification_payload` | string | The document the model receives if it requests verification. |
| `intervention_value_hint` | string | Human-authored description of the hint's epistemic value. |
| `intervention_value_verify` | string | Human-authored description of verification's epistemic value. |
| `optimal_first_action` | string | The epistemically correct first action: `answer`, `ask_hint`, `verify`, `abstain`. |
| `optimal_final_action` | string | The epistemically correct final decision: `answer` or `abstain`. |
| `acceptable_first_actions` | string | Pipe-separated list of first actions the scorer accepts without penalty. |
| `difficulty_band` | string | `easy`, `medium`, `hard`. Difficulty is operator-driven, not content-driven. |
| `generator_family` | string | Always `policy_world_v2`. |
| `policy_notes` | string | Human note on why the optimal action is what it is. |
| `operator_notes` | string | Human note on what the operator changes relative to the base world. |
| `hidden_fields` | string | Comma-separated list of field names hidden by the operator (if any). |
| `degraded_fields` | string | Comma-separated list of field names degraded by the operator (if any). |

**Recoverability types:**

| Value | Meaning |
|---|---|
| `fully_observable` | All required facts are visible. Direct answer is optimal. |
| `irrecoverable` | Missing or conflicting information cannot be resolved. Abstain is optimal. |
| `recoverable_by_verify` | Verification resolves or confirms the key fact. Verify-first is optimal. |
| `recoverable_by_hint` | A structured hint resolves the missing field. Ask-hint-first is optimal. |
| `partially_recoverable` | Intervention reduces uncertainty but cannot fully resolve it. |

---

## Bundle structure

Items are grouped into **100 bundles** of 9 items each. All items in a bundle share the same base world (`world_id`) and ask the same yes/no question. The 9 items apply the full set of operators to that world, so every world has one instance per operator slot. This structure allows per-bundle analysis and ensures that world-level confounders are controlled across operators.

---

## Operators

14 uncertainty operators covering four uncertainty families:

| Operator | n | Family | Optimal first | Optimal final |
|---|---|---|---|---|
| `none` | 170 | direct | answer | answer |
| `direct_answerable_hard` | 67 | direct | answer | answer |
| `answerable_weak_verify` | 66 | verification | verify | answer |
| `verify_residual_uncertainty` | 60 | verification | verify | abstain |
| `inject_policy_caveat` | 60 | verification | verify | answer |
| `inject_incomplete_record` | 60 | verification | verify | abstain |
| `inject_conflict` | 60 | conflict | abstain | abstain |
| `hide_exception` | 60 | hidden field | abstain | abstain |
| `hide_threshold` | 61 | hidden field | abstain | abstain |
| `inject_unverifiable_requirement` | 67 | hidden field | abstain | abstain |
| `make_rule_ambiguous` | 67 | hidden field | abstain | abstain |
| `irrecoverable_missing_record` | 66 | missing record | abstain | abstain |
| `hint_resolves_exception` | 19 | hint | ask\_hint | answer |
| `hint_resolves_missing_field` | 17 | hint | ask\_hint | answer |

**Optimal first-action distribution:** answer 33.7%, verify 33.3%, abstain 22.2%, ask_hint 10.8%  
**Optimal final-action distribution:** answer 64.4%, abstain 35.6%

---

## Known limitations

1. **Synthetic scenarios only.** All worlds are generated from templates. Linguistic diversity is limited; a model could learn surface patterns that signal the operator without learning the underlying epistemic skill.

2. **Policy domain only.** All items are policy eligibility decisions. The metacognitive skills measured (knowing when to verify, when to seek help, when to abstain) may not transfer to other domains.

3. **Binary final answer.** Final decisions are yes/no only. The benchmark does not measure calibration on multi-way or numeric answers.

4. **Hint-seeking is underrepresented.** Only 10.8% of items have `ask_hint` as the optimal first action, covering two operators (`hint_resolves_exception`, `hint_resolves_missing_field`) with small n (19 and 17 respectively). Hint-seeking scores are noisier than other action scores.

5. **No human spot-check on all items.** Generated items have not been reviewed row-by-row for logical consistency. Items where `optimal_first_action` conflicts with `verify_effect` or `hint_effect` may exist.

6. **`verify_residual_uncertainty` structural difficulty.** This operator is reliably the hardest across all models (Phase 8 max score: 0.388). It is unclear whether the difficulty reflects a genuine metacognitive gap or a prompt formulation artifact.

7. **Single surface per item.** Each item has exactly one `view_type`. Cross-view consistency is not enforced at the item level, only at the dataset level (225 per type).

8. **Dev split only.** This file is the development split. A held-out test split exists but is not included here. Dev-split scores may be inflated for models with exposure to similar templates.

---

## Intended use

- Benchmarking language models on **epistemic intervention control**: the ability to choose the right metacognitive action (answer, verify, seek help, abstain) given structured uncertainty.
- Ablation studies on scoring components, particularly intervention-value-alignment (IVA) vs outcome-only scoring.
- Operator-level diagnostic analysis to identify specific uncertainty types a model handles poorly.
- Development and validation of new uncertainty operators or policy scenario generators.

---

## Not intended use

- **Production policy decisions.** Scenarios are synthetic and should not be used to train or validate models for real eligibility determinations.
- **General NLU benchmarking.** The task requires explicit metacognitive action selection; models that do not expose an action API cannot be evaluated directly.
- **Out-of-domain transfer claims.** Results on this dataset should not be cited as evidence for general uncertainty quantification or calibration outside the policy eligibility domain.
- **Ranking models on outcome accuracy alone.** The dataset is designed so that outcome accuracy is a necessary but insufficient signal. Citing only `final_correct` rates misrepresents the benchmark's contribution.
