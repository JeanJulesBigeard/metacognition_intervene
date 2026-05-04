# mc_intervene_policy_v2.1 — Phase 8 Evaluation Summary

**Source run:** `outputs/eval_local_phase8_20260503_212137`  
**Dataset:** `mc_intervene_policy_v2_1_dev` — 900 items, 100 bundles, 14 operators  
**Date:** 2026-05-03/04

---

## Dataset and validation

- Dataset: `mc_intervene_policy_v2_1_dev`
- Rows: 900 (100 bundles × ~9 items per bundle)
- Operators: 14
- Optimal first action distribution: answer 33.7%, verify 33.3%, abstain 22.2%, ask_hint 10.8%
- Validation: **passed**
- Degenerate-policy gate: **passed** (all 6 blind policies within ceiling)

---

## Main result

`gemma4:31b` is the strongest local model with full-IVA score **0.784**. It beats the strongest blind degenerate policy, `verify_then_answer`, at 0.518 — a gap of **+0.266** (51% above the blind heuristic ceiling).

The top three models (gemma4:31b, gemma4:26b, qwen3.5:27b) all exceed the best blind heuristic. The bottom four do not, placing them in the same performance tier as the better degenerate policies.

---

## Leaderboard

| Rank | Model | full\_with\_iva | no\_iva | Δ | outcome | IVA | Behavior class |
|------|-------|----------------|---------|---|---------|-----|----------------|
| 1 | gemma4:31b | **0.784** | 0.817 | +0.033 | 0.799 | 0.699 | strong\_adaptive\_intervention\_averse |
| 2 | gemma4:26b | 0.708 | 0.744 | +0.036 | 0.692 | 0.613 | adaptive\_conservative |
| 3 | qwen3.5:27b | 0.688 | 0.750 | +0.062 | 0.748 | 0.533 | high\_outcome\_help\_seeker |
| 4 | olmo2:13b | 0.518 | 0.525 | +0.007 | 0.356 | 0.488 | conservative\_closure |
| 5 | mistral-small | 0.510 | 0.526 | +0.016 | 0.430 | 0.455 | mixed\_low\_control |
| 6 | qwen2.5:14b | 0.507 | 0.547 | +0.040 | 0.460 | 0.400 | help\_seeking\_collapse |
| 7 | deepseek-r1:32b | 0.436 | 0.403 | **−0.033** | 0.287 | 0.489 | over\_answering\_weak\_final\_policy |

Scores are recomputed from component columns using the v2.1_full formula without trajectory caps to enable clean ablation comparison.

---

## Degenerate baselines

| Policy | full\_with\_iva | no\_iva | Δ | outcome | IVA | Interpretation |
|--------|----------------|---------|---|---------|-----|----------------|
| oracle | 0.998 | 0.997 | −0.001 | 1.000 | 1.000 | Optimal trajectory; theoretical ceiling |
| direct\_gold\_answer | 0.564 | 0.577 | +0.013 | 0.644 | 0.383 | Omniscient cheat baseline |
| verify\_then\_answer | **0.518** | 0.507 | −0.011 | 0.644 | 0.409 | **Best blind heuristic** |
| always\_answer\_yes | 0.449 | 0.435 | −0.014 | 0.363 | 0.383 | Blind positive-answer |
| ask\_hint\_then\_answer | 0.442 | 0.450 | +0.008 | 0.644 | 0.138 | Blind hint-first |
| verify\_then\_abstain | 0.424 | 0.406 | −0.018 | 0.356 | 0.409 | Blind verify-first, abstain-final |
| always\_answer\_no | 0.414 | 0.395 | −0.020 | 0.281 | 0.383 | Blind negative-answer |
| always\_abstain | 0.407 | 0.421 | +0.014 | 0.356 | 0.339 | Conservative heuristic |
| ask\_hint\_then\_abstain | 0.336 | 0.354 | +0.018 | 0.356 | 0.138 | Low-value help-seeking |

---

## IVA ablation

IVA preserves the distinction between final-answer success and epistemic action quality. Without IVA:

- **qwen3.5:27b overtakes gemma4:26b** (0.750 vs 0.744 no-IVA; 0.688 vs 0.708 full-IVA). High outcome + lower IVA gets rewarded when IVA is removed.
- **deepseek-r1:32b uniquely falls** (−0.033). Its IVA (0.489) is high relative to its outcome (0.287); removing IVA lets the poor outcome dominate.
- All other models score higher without IVA, but ranks mostly preserve — IVA is not distorting the top of the table, it is providing trajectory-quality signal that refines relative ordering.

**IVA as trajectory-quality discriminator (not degenerate-policy suppressor):**
`verify_then_answer` and `ask_hint_then_answer` have identical outcome (0.644) but IVA 0.409 vs 0.138. Under full scoring, their gap is 0.076 (0.518 vs 0.442). Under no-IVA, the gap collapses to 0.057. IVA is rewarding the verify-first trajectory because verification is epistemically correct on 33% of the dataset; hint-first is only correct on 11%.

---

## Operator-level findings

| Finding | Operators | Models |
|---------|-----------|--------|
| Universally easy (score ≥ 1.0 for most) | `hint_resolves_exception`, `hint_resolves_missing_field` | All except olmo2 |
| Gemma strength | `inject_conflict`, `irrecoverable_missing_record`, `make_rule_ambiguous` | gemma4:31b, gemma4:26b |
| Qwen strength, Gemma weakness | `hide_threshold` | qwen3.5, qwen2.5 lead; gemma4:31b = 0.235 |
| DeepSeek anomaly | `inject_policy_caveat` | deepseek-r1 = 0.975, others ≤ 0.548 |
| Universally hard | `verify_residual_uncertainty` | All models ≤ 0.388 |
| olmo2 sole failure | `hint_resolves_*` | olmo2 = 0.248–0.312; all others = 1.000 |

---

## Behavioral taxonomy

| Model | Class | Signature |
|-------|-------|-----------|
| gemma4:31b | strong\_adaptive\_intervention\_averse | Direct answer/abstain; selective verify; calibrated |
| gemma4:26b | adaptive\_conservative | High abstain rate (44%); threshold-aware |
| qwen3.5:27b | high\_outcome\_help\_seeker | ask\_hint first 51%; good outcomes via escalation |
| qwen2.5:14b | help\_seeking\_collapse | ask\_hint first 67%; over-abstains; IVA lowest |
| olmo2:13b | conservative\_closure | 100% final abstain; verify-first but never commits |
| mistral-small | mixed\_low\_control | Mixed first-action; no dominant failure mode |
| deepseek-r1:32b | over\_answering\_weak\_final\_policy | 99% final answer; answers non-answerable cases |

---

## Main scientific claim

`mc_intervene_policy_v2.1` separates final-answer correctness from epistemic action selection. The results show that current local models often know what final answer to give, but fail to choose the epistemic action that would make that answer justified.

The clearest illustration: `qwen3.5:27b` achieves outcome accuracy 0.748 (second best) but asks for hints 50.8% of the time including on operators where direct answering or verification is optimal. `deepseek-r1:32b` performs the first action correctly (IVA=0.489) but ignores the result and answers regardless (99% answer rate), producing the worst outcome accuracy in the suite.

Neither pattern is visible from outcome scores alone. IVA and operator-level diagnostics are necessary to see them.

---

*Full evaluation report: `reports/phase8_frontier_lab_report.md`*  
*All CSVs: `outputs/phase8_report_20260503_212137/`*
