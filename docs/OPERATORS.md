# Uncertainty Operators — mc_intervene v2

Each operator injects a specific type of epistemic gap into an otherwise solvable policy scenario. The gap determines the optimal first action and whether the case is ultimately answerable.

## Operator taxonomy

### Direct / answerable

| Operator | n | Description | Optimal first | Optimal final |
|---|---|---|---|---|
| `none` | 170 | All facts visible; no uncertainty | answer | answer |
| `direct_answerable_hard` | 67 | All facts visible but requires careful inference | answer | answer |
| `answerable_weak_verify` | 66 | Verify confirms but is not strictly needed | verify | answer |

### Verification-recoverable

| Operator | n | Description | Optimal first | Optimal final |
|---|---|---|---|---|
| `inject_policy_caveat` | 60 | A document clause qualifies the base rule; verify resolves it | verify | answer |
| `inject_incomplete_record` | 60 | Record is missing a field; verify partially resolves | verify | abstain |
| `verify_residual_uncertainty` | 60 | Verify confirms document but epistemic residual remains; should abstain after verifying | verify | abstain |

### Hint-recoverable

| Operator | n | Description | Optimal first | Optimal final |
|---|---|---|---|---|
| `hint_resolves_exception` | 19 | A policy exception is unknown; hint reveals it | ask\_hint | answer |
| `hint_resolves_missing_field` | 17 | A field value is missing; hint surfaces it | ask\_hint | answer |

### Conflict / irrecoverable

| Operator | n | Description | Optimal first | Optimal final |
|---|---|---|---|---|
| `inject_conflict` | 60 | Two document clauses contradict each other | abstain | abstain |
| `hide_exception` | 60 | A policy exception exists but is not disclosed | abstain | abstain |
| `hide_threshold` | 61 | A numerical threshold is redacted | abstain | abstain |
| `inject_unverifiable_requirement` | 67 | A required fact cannot be verified from available sources | abstain | abstain |
| `make_rule_ambiguous` | 67 | The policy rule is grammatically or semantically ambiguous | abstain | abstain |
| `irrecoverable_missing_record` | 66 | A required record does not exist | abstain | abstain |

## Dataset distribution

| Property | Value |
|---|---|
| Optimal first action: `answer` | 303 (33.7%) |
| Optimal first action: `verify` | 300 (33.3%) |
| Optimal first action: `abstain` | 200 (22.2%) |
| Optimal first action: `ask_hint` | 97 (10.8%) |
| Optimal final action: `answer` | 580 (64.4%) |
| Optimal final action: `abstain` | 320 (35.6%) |

## Verify effects

What the verification payload reveals, by operator:

| Effect | n | Meaning |
|---|---|---|
| `confirm` | 357 | Document fully confirms the claim |
| `insufficient` | 230 | Document exists but does not resolve the question |
| `residual_uncertainty` | 120 | Document confirms but epistemic residual remains |
| `ambiguous_support` | 67 | Document is compatible with multiple conclusions |
| `weak_confirm` | 66 | Document provides weak confirmation |
| `warn` | 60 | Document contradicts or qualifies the claim |

## Hint effects

| Effect | n | Meaning |
|---|---|---|
| `none` | 556 | Hint provides no useful information |
| `partial` | 247 | Hint narrows uncertainty but does not resolve it |
| `resolve` | 97 | Hint fully resolves the missing information |

## Phase 8 operator diagnostics

Scores from the 7-model Phase 8 run (`full_with_iva`, sorted by cross-model mean):

| Operator | gemma4:31b | gemma4:26b | qwen3.5 | mistral | qwen2.5 | olmo2 | deepseek-r1 |
|---|---|---|---|---|---|---|---|
| `hint_resolves_exception` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.312 | 1.000 |
| `hint_resolves_missing_field` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.248 | 1.000 |
| `direct_answerable_hard` | 0.993 | 0.963 | 0.949 | 0.509 | 0.583 | 0.238 | 0.568 |
| `answerable_weak_verify` | 0.948 | 0.855 | 0.925 | 0.502 | 0.583 | 0.312 | 0.831 |
| `none` | 0.939 | 0.763 | 0.920 | 0.496 | 0.431 | 0.203 | 0.619 |
| `irrecoverable_missing_record` | 1.000 | 1.000 | 0.538 | 0.500 | 0.500 | 0.975 | 0.078 |
| `make_rule_ambiguous` | 0.920 | 0.869 | 0.500 | 0.500 | 0.500 | 0.975 | 0.117 |
| `inject_policy_caveat` | 0.904 | 0.487 | 0.625 | 0.548 | 0.155 | 0.442 | 0.975 |
| `inject_unverifiable_requirement` | 0.826 | 0.552 | 0.500 | 0.228 | 0.494 | 0.975 | 0.171 |
| `inject_conflict` | 0.637 | 0.839 | 0.189 | 0.171 | 0.171 | 0.410 | 0.149 |
| `hide_exception` | 0.539 | 0.360 | 0.342 | 0.311 | 0.241 | 0.393 | 0.440 |
| `inject_incomplete_record` | 0.192 | 0.245 | 0.551 | 0.520 | 0.550 | 0.412 | 0.106 |
| `hide_threshold` | 0.235 | 0.297 | 0.491 | 0.430 | 0.486 | 0.253 | 0.404 |
| `verify_residual_uncertainty` | 0.277 | 0.281 | 0.300 | 0.300 | 0.388 | 0.300 | 0.073 |

Full per-operator CSVs: [`reports/tables/operator_scores_by_model.csv`](../reports/tables/operator_scores_by_model.csv)
