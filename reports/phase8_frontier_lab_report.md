# mc_intervene v2.1: Frontier-Lab Phase 8 Evaluation Report

**Run date:** 2026-05-03/04  
**Artifact directory:** `outputs/phase8_report_20260504_215029/`  
**Dataset:** `mc_intervene_policy_v2_1_dev` (900 items, 100 bundles, 14 operators)  
**Models evaluated:** 7 (gemma4:31b, gemma4:26b, qwen3.5:27b, olmo2:13b, mistral-small, qwen2.5:14b, deepseek-r1:32b)

---

## Executive summary

mc_intervene v2.1 is a benchmark for epistemic decision-making under uncertainty. A model agent receives a policy question and must decide: answer directly, request a hint, verify a supporting document, or abstain. The benchmark rewards not just correct final answers but correct *epistemic trajectories* — choosing the right intervention at the right time.

**Five headline findings from Phase 8:**

1. **Degenerate baselines are controlled.** No blind heuristic exceeds its release-gate ceiling. The best blind strategy (verify-first, answer-final) scores 0.518. The best model (gemma4:31b) scores 0.750 — a 44.8% absolute gap over the ceiling of mindless behavior.

2. **Adaptive models clearly beat the best blind heuristic.** All three top models (gemma4:31b, gemma4:26b, qwen3.5:27b) exceed 0.518 by a wide margin. The bottom four do not, placing them in the same performance tier as the better degenerate policies.

3. **Models separate into six behaviorally distinct classes.** Gemma models make calibrated direct decisions; Qwen models over-use hint-seeking; olmo2 compulsively abstains; deepseek-r1 confidently over-answers; mistral-small hedges without strong bias.

4. **IVA is a trajectory-quality discriminator, not a degenerate-policy suppressor.** Removing IVA from the scoring formula changes model rank (deepseek-r1 falls −0.033 without IVA; qwen3.5 rises +0.062). Among degenerate policies, verify-first trajectories (IVA=0.41) fall without IVA while hint-first policies (IVA=0.14) rise — confirming IVA tracks epistemic path quality, not just outcome.

5. **Operator diagnostics reveal targeted failure modes.** `verify_residual_uncertainty` is universally hard (all models ≤ 0.388). `inject_conflict` separates Gemma from Qwen/DeepSeek sharply. `hint_resolves_*` operators expose olmo2 as the only model unable to seek structured help even when it would resolve the case.

---

## Benchmark objective

mc_intervene v2.1 operationalises the following claim: *a model that makes correct final decisions by the wrong epistemic route is less trustworthy than one that takes the correct route, even at the same outcome accuracy.*

Concretely, the benchmark distinguishes:

| Trajectory | Description | Example |
|---|---|---|
| `answer` | Direct answer, no intervention | answerable case, high confidence |
| `ask_hint → answer/abstain` | Seek structured hint, then decide | missing field resolvable by hint |
| `verify → answer/abstain` | Verify a document, then decide | clause with ambiguous confirmation |
| `abstain` | Refuse to answer | irrecoverable missing record |

Each operator in the dataset creates a specific type of uncertainty that favors one trajectory over others. The score formula (`v2_1_full`) rewards outcome accuracy (35%), trajectory quality via IVA (30%), policy control (20%), calibration (10%), and efficiency (5%).

---

## Dataset construction

**Dataset:** `mc_intervene_policy_v2_1_dev`

| Property | Value |
|---|---|
| Total items | 900 |
| Bundles (paired groups) | 100 |
| Operators | 14 |
| Task family | `mc_intervene_v2` |
| Optimal first action: `answer` | 303 (33.7%) |
| Optimal first action: `verify` | 300 (33.3%) |
| Optimal first action: `abstain` | 200 (22.2%) |
| Optimal first action: `ask_hint` | 97 (10.8%) |
| Optimal final action: `answer` | 580 (64.4%) |
| Optimal final action: `abstain` | 320 (35.6%) |

**Operator distribution:**

| Operator | n | Optimal first action |
|---|---|---|
| `none` (direct answerable) | 170 | answer |
| `direct_answerable_hard` | 67 | answer |
| `answerable_weak_verify` | 66 | verify |
| `hide_threshold` | 61 | abstain |
| `hide_exception` | 60 | abstain |
| `inject_conflict` | 60 | abstain |
| `inject_incomplete_record` | 60 | verify |
| `inject_policy_caveat` | 60 | verify |
| `inject_unverifiable_requirement` | 67 | abstain |
| `irrecoverable_missing_record` | 66 | abstain |
| `make_rule_ambiguous` | 67 | abstain |
| `verify_residual_uncertainty` | 60 | verify |
| `hint_resolves_exception` | 19 | ask\_hint |
| `hint_resolves_missing_field` | 17 | ask\_hint |

Each item is a fully specified insurance/policy decision scenario in one of several surface variants (short narrative, policy excerpt). Operators inject controlled uncertainty: `inject_conflict` plants a contradictory document clause; `hide_threshold` omits a critical threshold value; `hint_resolves_*` operators provide resolvable cases where a structured hint (but not direct document verification) would unlock the answer.

---

## Validation and release gates

Dataset validation runs before every model evaluation pass and checks:

- Row count and bundle completeness
- Required column presence and type validity
- No null values in scoring columns
- Operator-policy consistency (`EXPECTED_OPERATOR_POLICY` mapping)
- Optimal first-action distribution within bounds (`MIN_FIRST_ACTION_PCT`, `MAX_FIRST_ACTION_PCT`)

**Phase 8 validation result:** PASS (900 rows, 100 bundles).

**Degenerate-policy gate** (exits 1 if any blind policy breaches its ceiling):

| Policy | Score | Ceiling | Status |
|---|---|---|---|
| `always_abstain` | 0.407 | 0.42 | PASS ✓ |
| `always_answer_no` | 0.414 | 0.45 | PASS ✓ |
| `always_answer_yes` | 0.449 | 0.45 | PASS ✓ |
| `ask_hint_then_abstain` | 0.336 | 0.40 | PASS ✓ |
| `verify_then_abstain` | 0.424 | 0.45 | PASS ✓ |
| `verify_then_answer` | 0.518 | 0.55 | PASS ✓ |

All 6 policies within threshold. The gate confirms the benchmark's discrimination power: no fixed strategy can achieve a score high enough to be mistaken for competent adaptive behavior.

---

## Degenerate-policy audit

The full degenerate-policy table is in `degenerate_baseline_table.csv`. The oracle baseline (always optimal) provides the theoretical ceiling.

| Policy | final\_score | outcome | IVA | Interpretation |
|---|---|---|---|---|
| oracle | 0.998 | 1.000 | 1.000 | Optimal trajectory; theoretical ceiling |
| direct\_gold\_answer | 0.564 | 0.644 | 0.383 | Omniscient latent-truth cheat |
| **verify\_then\_answer** | **0.518** | **0.644** | **0.409** | Best blind heuristic |
| always\_answer\_yes | 0.449 | 0.363 | 0.383 | Blind positive-answer |
| ask\_hint\_then\_answer | 0.442 | 0.644 | 0.138 | Blind hint-first, answer-final |
| verify\_then\_abstain | 0.424 | 0.356 | 0.409 | Blind verify-first, abstain-final |
| always\_answer\_no | 0.414 | 0.281 | 0.383 | Blind negative-answer |
| always\_abstain | 0.407 | 0.356 | 0.339 | Conservative heuristic |
| ask\_hint\_then\_abstain | 0.336 | 0.356 | 0.138 | Low-value help-seeking |

**Key observations:**

- `verify_then_answer` and `direct_gold_answer` share identical outcome accuracy (0.644) — the gold baseline cheats by knowing the ground truth, yet scores only 0.564 vs 0.518 for blind verify-then-answer. The gap (0.046) reflects better IVA and control in the oracle trajectory.
- `ask_hint_then_answer` also achieves outcome=0.644 but scores only 0.442 because asking a hint before answering (when verify or direct answer was optimal) misaligns trajectory — IVA=0.138 vs 0.409 for verify-then-answer.
- `ask_hint_then_abstain` is the weakest policy (0.336) because it spends an inefficient token on a hint and then fails to commit.
- Trajectory caps (applied when the model bypasses an available intervention or takes the wrong final action) explain why some policies with high outcome scores still have suppressed final scores.

---

## Main model leaderboard

Source: `phase8_model_leaderboard.csv` (mean over 900 items per model).

| Rank | Model | final\_score | outcome | IVA | control | calibration | efficiency | correct\_rate |
|---|---|---|---|---|---|---|---|---|
| 1 | gemma4:31b | **0.750** | 0.799 | 0.699 | 0.826 | 0.804 | 0.982 | 0.799 |
| 2 | gemma4:26b | 0.665 | 0.692 | 0.613 | 0.787 | 0.753 | 0.981 | 0.692 |
| 3 | qwen3.5:27b | 0.633 | 0.748 | 0.533 | 0.759 | 0.678 | 0.936 | 0.748 |
| 4 | olmo2:13b | 0.455 | 0.356 | 0.488 | 0.623 | 0.753 | 0.951 | 0.356 |
| 5 | mistral-small | 0.452 | 0.430 | 0.455 | 0.651 | 0.462 | 0.934 | 0.430 |
| 6 | qwen2.5:14b | 0.451 | 0.460 | 0.400 | 0.638 | 0.534 | 0.912 | 0.460 |
| 7 | deepseek-r1:32b | 0.431 | 0.287 | 0.489 | 0.525 | 0.371 | 0.935 | 0.287 |

**Notes:**

- `final_score` includes trajectory caps (hard penalties for bypassing available interventions or choosing wrong final actions). The IVA ablation table uses uncapped formula recomputation for clean comparison.
- gemma4:31b (0.750) exceeds the best blind heuristic (0.518) by **+0.232** (+44.8%). This is the primary adaptive-beats-heuristic signal.
- qwen3.5:27b ranks 3rd in final_score but has the second-highest outcome accuracy (0.748), slightly behind gemma4:31b (0.799). Its IVA (0.533) is lower — it achieves good outcomes via a less optimal trajectory.
- olmo2:13b has the highest calibration (0.753) despite the lowest outcome (0.356) — it is well-calibrated about how often it is correct, which is consistently "never" for answerable cases.
- deepseek-r1:32b has the lowest outcome (0.287) despite moderate IVA (0.489) — it picks appropriate first actions but ignores their signal and answers regardless.

---

## Behavioral taxonomy

Six distinct behavioral profiles emerge from the action distribution data.

**Action distributions (% of 900 items):**

| Model | first: answer | first: ask\_hint | first: verify | first: abstain | final: answer | final: abstain |
|---|---|---|---|---|---|---|
| gemma4:31b | 53.7% | 4.0% | 8.2% | 34.1% | 65.6% | 34.4% |
| gemma4:26b | 45.8% | 5.6% | 4.9% | 43.8% | 54.7% | 45.3% |
| qwen3.5:27b | 36.7% | 50.8% | 5.3% | 7.2% | 54.3% | 45.7% |
| mistral-small | 39.3% | 44.7% | 9.3% | 6.7% | 60.2% | 39.8% |
| qwen2.5:14b | 27.3% | 66.6% | 1.7% | 4.4% | 43.2% | 56.8% |
| olmo2:13b | 0.0% | 0.7% | 44.8% | 54.6% | 0.0% | 100.0% |
| deepseek-r1:32b | 55.6% | 37.6% | 6.9% | 0.0% | 98.9% | 1.1% |

### Class 1 — Calibrated intervention (gemma4:31b, gemma4:26b)

Both Gemma models make direct first-move decisions — mostly answer or abstain — with moderate use of verify and minimal hint-seeking. They achieve high IVA because they choose the right first action type, not because they systematically escalate. gemma4:31b abstains first 34% of the time; gemma4:26b 44%. Both have final abstain rates close to the true unanswerable rate (35.6%), suggesting they are calibrated to the dataset's answer/abstain balance.

### Class 2 — Escalating answerer (qwen3.5:27b)

qwen3.5:27b asks for hints 50.8% of the time on the first move, yet achieves outcome=0.748 (second best). This works because many of its hint-seeking episodes fall on `inject_incomplete_record`, `inject_conflict`, and similar operators where a hint can partially resolve uncertainty. Its final abstain rate (45.7%) is modestly higher than the true rate (35.6%) — it sometimes escalates correctly but over-uses the safety valve.

### Class 3 — Compulsive abstainer (olmo2:13b)

olmo2 abstains on 100% of final decisions. It never answers. It tries verify first on 44.8% of cases but then abstains regardless of the result. Outcome=0.356 is exactly the dataset abstain-optimal fraction (35.6% of items have optimal final action = abstain), confirming olmo2 is right only when the correct answer is to refuse. IVA=0.488 reflects that its first-action choices (verify + abstain) are sometimes correct relative to the operator, but the second-step logic is absent.

### Class 4 — Confident over-answerer (deepseek-r1:32b)

deepseek-r1 answers on 98.9% of final decisions. It never abstains when it should. Outcome=0.287 is below the direct-answer baseline because answering on unanswerable cases (35.6% of items) is penalized heavily. Its IVA=0.489 is moderate because it sometimes chooses verify or ask_hint as a first action (44.5% combined), but these interventions do not change its final decision — it answers regardless. The reasoning model's chain-of-thought may systematically resolve uncertainty toward confident answers.

### Class 5 — Cautious hedge (mistral-small)

mistral-small has a mixed first-action distribution (ask_hint 44.7%, answer 39.3%, verify 9.3%, abstain 6.7%) without a dominant mode. Its final answer rate (60.2%) is close to the true answerable fraction (64.4%). It achieves median performance with no distinctive failure mode — neither over-abstaining nor over-answering severely.

### Class 6 — Over-helping, under-committing (qwen2.5:14b)

qwen2.5:14b asks for hints 66.6% of the time — the highest in the cohort — yet achieves only outcome=0.460. Hint-seeking followed by abstain accounts for a large share of its final decisions (56.8% abstain). On operators where hints do not fully resolve uncertainty (`inject_conflict`, `hide_threshold`), this strategy incurs the efficiency cost without the outcome benefit. Its final_score (0.451) is nearly identical to mistral-small despite a very different behavioral profile.

---

## Operator-level diagnostics

Source: `operator_scores_by_model.csv`. Full tables with action rates in `operator_first_action_rates_by_model.csv` and `operator_final_action_rates_by_model.csv`.

### Final scores by model × operator (pivot)

| Operator | gemma4:31b | gemma4:26b | qwen3.5:27b | mistral | qwen2.5 | olmo2 | deepseek-r1 |
|---|---|---|---|---|---|---|---|
| hint\_resolves\_exception | **1.000** | **1.000** | **1.000** | **1.000** | **1.000** | 0.312 | **1.000** |
| hint\_resolves\_missing\_field | **1.000** | **1.000** | **1.000** | **1.000** | **1.000** | 0.248 | **1.000** |
| irrecoverable\_missing\_record | **1.000** | **1.000** | 0.538 | 0.500 | 0.500 | 0.975 | 0.078 |
| make\_rule\_ambiguous | 0.920 | 0.869 | 0.500 | 0.500 | 0.500 | 0.975 | 0.117 |
| answerable\_weak\_verify | 0.948 | 0.855 | 0.925 | 0.502 | 0.583 | 0.312 | 0.831 |
| direct\_answerable\_hard | 0.993 | 0.963 | 0.949 | 0.509 | 0.583 | 0.238 | 0.568 |
| inject\_policy\_caveat | 0.904 | 0.487 | 0.625 | 0.548 | 0.155 | 0.442 | 0.975 |
| inject\_unverifiable\_requirement | 0.826 | 0.552 | 0.500 | 0.228 | 0.494 | 0.975 | 0.171 |
| none (direct) | 0.939 | 0.763 | 0.920 | 0.496 | 0.431 | 0.203 | 0.619 |
| inject\_incomplete\_record | 0.192 | 0.245 | 0.551 | 0.520 | 0.550 | 0.412 | 0.106 |
| inject\_conflict | 0.637 | 0.839 | 0.189 | 0.171 | 0.171 | 0.410 | 0.149 |
| hide\_exception | 0.539 | 0.360 | 0.342 | 0.311 | 0.241 | 0.393 | 0.440 |
| hide\_threshold | 0.235 | 0.297 | **0.491** | 0.430 | **0.486** | 0.253 | 0.404 |
| verify\_residual\_uncertainty | 0.277 | 0.281 | 0.300 | 0.300 | 0.388 | 0.300 | 0.073 |

### Operator-level findings

**Universally easy (most models ≥ 0.9):**
- `hint_resolves_exception` and `hint_resolves_missing_field`: 6/7 models score 1.000. olmo2 is the sole failure (0.312/0.248), demonstrating that its inability to use hints costs it on every hint-resolvable case.
- `direct_answerable_hard` and `none`: Top 3 models score 0.92–0.99. Lower-tier models (mistral-small, qwen2.5) score only 0.50–0.58 — they do not reliably commit to direct answers even when the case is unambiguously answerable.

**Operator that separates Gemma from the field — `inject_conflict`:**
gemma4:26b (0.839) and gemma4:31b (0.637) are the only models scoring above 0.5. All others (qwen3.5: 0.189, deepseek: 0.149, qwen2.5: 0.171, mistral: 0.171) fail to identify conflicting evidence and default to wrong final decisions. This single operator captures whether a model can recognise and flag document conflicts rather than picking a side.

**Operator that separates qwen from Gemma — `hide_threshold`:**
qwen3.5 (0.491) and qwen2.5 (0.486) lead; gemma4:31b scores only 0.235. `hide_threshold` items omit a numerical cutoff — the model should abstain, but gemma4:31b over-commits to verify and then answers incorrectly. Qwen models' tendency to ask for hints is beneficial here: the hint partially surfaces the missing threshold.

**Operators that expose olmo2's abstain lock:**
On `direct_answerable_hard` (0.238) and `none` (0.203), olmo2 scores near the floor despite these being the simplest cases. Because it always abstains finally, it fails every answerable case.

**Universally hard operator — `verify_residual_uncertainty`:**
No model scores above 0.388. This operator presents a case where verification confirms the document but leaves epistemic residual uncertainty (the model should abstain after verifying). The correct trajectory is: `verify → abstain`. Most models either abstain immediately (skipping verify) or answer after verify (ignoring the residual signal). deepseek-r1 scores 0.073 — it answers regardless of residual uncertainty.

**Emergent finding — `inject_policy_caveat`:**
deepseek-r1 scores 0.975 on `inject_policy_caveat` (the operator injects a policy exception clause). deepseek's reasoning traces appear to explicitly enumerate exceptions when present, making it the strongest model on this specific operator despite being last overall. gemma4:26b scores only 0.487 here.

---

## IVA ablation

Source: `iva_ablation_model_table.csv` and `degenerate_iva_ablation_table.csv`.

The IVA component (weight 0.30) measures whether the chosen first action matches the optimal first action for the operator. The ablation compares:
- `full_with_iva`: 0.35·outcome + 0.30·IVA + 0.20·control + 0.10·calibration + 0.05·efficiency
- `no_iva`: 0.50·outcome + 0.30·control + 0.15·calibration + 0.05·efficiency (IVA weight redistributed)

Scores are recomputed from component columns without trajectory caps, so deltas reflect pure formula-level impact.

### Model-level ablation

| Model | full\_with\_iva | no\_iva | Δ (no\_iva − full) |
|---|---|---|---|
| gemma4:31b | 0.784 | 0.817 | +0.033 |
| gemma4:26b | 0.708 | 0.744 | +0.036 |
| qwen3.5:27b | 0.688 | 0.750 | **+0.062** |
| olmo2:13b | 0.518 | 0.525 | +0.007 |
| mistral-small | 0.510 | 0.526 | +0.016 |
| qwen2.5:14b | 0.507 | 0.547 | +0.040 |
| **deepseek-r1:32b** | **0.436** | **0.403** | **−0.033** |

**Key finding:** deepseek-r1 is the only model that falls without IVA. Its IVA (0.489) is disproportionately high relative to its outcome (0.287). Under no-IVA scoring, its poor outcome dominates. This is the clearest evidence that IVA captures something orthogonal to outcome: deepseek-r1 chooses appropriate *first actions* but then ignores their signal, producing a model that has good epistemic intent but poor epistemic follow-through.

qwen3.5:27b shows the largest positive Δ (+0.062). Its outcome (0.748) is high but its IVA (0.533) is moderate — removing IVA gives it more credit for outcome and less penalty for trajectory, inflating its apparent ranking. Under full-IVA scoring, gemma4:26b (IVA=0.613) stays ahead of qwen3.5 (IVA=0.533) in the combined formula even though qwen3.5 has higher outcome.

**IVA preserves the Gemma/Qwen distinction at the trajectory level.** Without IVA, qwen3.5 (no_iva=0.750) overtakes gemma4:26b (no_iva=0.744). With full IVA, gemma4:26b (0.708) leads qwen3.5 (0.688) — reflecting that Gemma's trajectories are more consistent with optimal epistemic paths.

### Degenerate-policy ablation

| Policy | full\_with\_iva | no\_iva | Δ | IVA score | Trajectory quality |
|---|---|---|---|---|---|
| oracle | 0.998 | 0.997 | −0.001 | 1.000 | Optimal |
| direct\_gold\_answer | 0.564 | 0.577 | +0.013 | 0.383 | Cheat, mixed trajectory |
| **verify\_then\_answer** | **0.518** | **0.507** | **−0.011** | **0.409** | Verify-first (high quality) |
| always\_answer\_yes | 0.449 | 0.435 | −0.014 | 0.383 | Blind answer (medium quality) |
| ask\_hint\_then\_answer | 0.442 | 0.450 | +0.008 | 0.138 | Hint-first (low quality) |
| verify\_then\_abstain | 0.424 | 0.406 | −0.018 | 0.409 | Verify-first (high quality) |
| always\_answer\_no | 0.414 | 0.395 | −0.020 | 0.383 | Blind answer (medium quality) |
| always\_abstain | 0.407 | 0.421 | +0.014 | 0.339 | No intervention (low quality) |
| ask\_hint\_then\_abstain | 0.336 | 0.354 | +0.018 | 0.138 | Hint-first (low quality) |

**IVA as a trajectory-quality discriminator:**

The sign of Δ tracks IVA score:
- Policies with IVA ≥ 0.383 (verify-first, blind-answer): all have Δ ≤ 0 — they *fall* without IVA. IVA is rewarding their trajectory quality.
- Policies with IVA = 0.138 (hint-first): Δ = +0.008 to +0.018 — they *rise* without IVA. IVA is correctly penalising their wasteful hint-seeking.
- `always_abstain` (IVA=0.339): Δ = +0.014 — it rises without IVA because its outcome (0.356) is low and IVA provides no lift; removing IVA lets outcome dominate at a higher weight, which marginally helps.

This confirms the central design claim: **IVA does not merely suppress degenerate policies. It discriminates among policies by the quality of their epistemic path.** Two policies with identical outcome accuracy (e.g., verify_then_answer vs ask_hint_then_answer, both 0.644 outcome) are separated by 0.076 in final_score under full IVA — a gap that collapses to 0.056 without IVA and would collapse entirely if only outcome were scored.

---

## Limitations

1. **Local models only.** Phase 8 covers 7 open-weights models run locally via Ollama. Frontier hosted models (GPT-4o, Claude 3.5, Gemini 1.5 Pro) are not yet evaluated. The current leaderboard does not generalise to that tier.

2. **Dev split only.** All results are on the dev split (900 items). A held-out test split exists but has not been evaluated; dev-set contamination from prompt tuning cannot be ruled out for models trained after the dataset's public release date.

3. **No human spot-check.** Approximately 30–50 generated items have not been human-reviewed. Systematic generation artifacts (e.g., impossible operator combinations, underspecified policies) may inflate or deflate specific operator scores.

4. **Trajectory caps are heuristic.** The `apply_v2_score_caps` function applies hard per-combination score ceilings (e.g., cap=0.30 when the model bypasses a needed intervention to abstain directly). These ceilings were set judgmentally in v2.1 and have not been validated against human preference scores.

5. **IVA scores `ask_hint` uniformly.** The IVA function rewards the model for choosing `ask_hint` when the oracle would. It does not distinguish between a partial hint (IVA credit earned) and a useless hint request (IVA credit still earned because the first action type was right). This may overestimate hint-seeking quality for operators where hints are partially but not fully resolvable.

6. **Single-sample evaluation.** Each model is evaluated once per item. No temperature sampling or majority-vote decoding. Stochastic variation is not characterised.

---

## Next work

| Priority | Task |
|---|---|
| High | Evaluate frontier hosted models (GPT-4o, Claude 3.5 Sonnet, Gemini 1.5 Pro) against the same 900-item dev split |
| High | Human spot-check of 30–50 generated items; correct or remove systematic artifacts |
| High | Held-out test split evaluation to validate dev-split findings |
| Medium | Multi-sample evaluation (temperature sweep or 3-seed majority vote) to characterise variance, especially for borderline operators |
| Medium | Refine `apply_v2_score_caps` thresholds using human preference scores on 100 annotated trajectories |
| Medium | IVA sub-component analysis: distinguish first-action type match from first-action confidence alignment |
| Low | Dataset card with limitations, operator taxonomy, and generation provenance |
| Low | Cross-operator clustering: group operators by model difficulty profile (e.g., PCA over model × operator score matrix) |

---

*Generated from Phase 8 run `eval_local_phase8_20260503_212137`. All CSVs in `outputs/phase8_report_20260504_215029/`. Script: `scripts/build_phase8_tables.py`.*
