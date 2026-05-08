# Scoring — mc_intervene

## v1 scoring

Used by `task_family = "mc_intervene_v1"` (arithmetic scenarios).

```
final_score = 0.35 × outcome
            + 0.30 × control
            + 0.15 × calibration
            + 0.10 × confidence_dynamics
            + 0.10 × efficiency
```

### Outcome (35%)

Binary correctness of the final answer or abstention decision.

### Control (30%)

Composite of first-action quality, transition quality, and final-policy quality:

```
control = 0.45 × first_action_score
        + 0.25 × transition_score
        + 0.30 × final_policy_score
```

### Calibration (15%)

Proper scoring rule applied to the model's stated confidence vs the binary correctness outcome.

### Confidence Dynamics (10%)

Whether confidence moves in the right direction after an intervention (e.g., rises after confirmation, falls after a warning).

### Efficiency (10%)

Penalises unnecessary interventions (requesting a hint or verify when a direct answer was epistemically justified).

---

## v2 scoring (`mc_intervene_v2`)

Used by `task_family = "mc_intervene_v2"` (policy scenarios). Elevates **intervention value alignment** and collapses confidence dynamics.

### v2_1_full formula

```
final_score = 0.35 × outcome_score
            + 0.30 × intervention_value_alignment_score
            + 0.20 × control_score
            + 0.10 × calibration_score
            + 0.05 × efficiency_score
```

### v2_1_no_iva formula (ablation)

IVA weight (0.30) redistributed proportionally to outcome and control:

```
final_score = 0.50 × outcome_score
            + 0.30 × control_score
            + 0.15 × calibration_score
            + 0.05 × efficiency_score
```

### Intervention Value Alignment (IVA)

Scores whether the model's first action matches the epistemically optimal first action:

| Chosen action vs optimal | Score |
|---|---|
| Matches optimal | 1.0 |
| In acceptable alternatives | 0.5 |
| Intervention with value `high` | 1.0 |
| Intervention with value `medium` | 0.5 |
| Intervention with value `low` | 0.15 |
| Intervention with value `negative` | 0.0 |

### Control score (v2)

```
control = 0.45 × first_action_score
        + 0.25 × transition_score
        + 0.30 × final_policy_score
```

`transition_score` = 1.0 for abstain-first or no-second-action episodes; otherwise scores whether the second action appropriately follows from the intervention result.

### Score ceilings

Hard caps applied after the formula for systematically wrong trajectory patterns:

| Pattern | Ceiling |
|---|---|
| Final abstain when answer was optimal | 0.45 |
| Final answer when abstain was optimal | 0.35 |
| Direct answer when intervention was optimal | 0.60 |
| Abstain directly when intervention was available | 0.30 |
| Wrong intervention type (hint when verify needed, or vice versa) | 0.55 |
| Wasted intervention when direct answer was optimal | 0.55 |
| Wasted intervention when immediate abstain was optimal | 0.50 |

### Two score families

| Family | Trajectory caps | Used for |
|---|---|---|
| Operational (capped) | Yes | Runtime eval, release gate, `.txt` outputs |
| Ablation (uncapped) | No | IVA ablation comparison, `reports/tables/` |

Ablation scores average ~+0.03 higher than operational scores because trajectory caps are not applied. The ablation scores are computed from per-item component columns in the `per_item/` CSVs, not from the `final_score` column directly.

---

## Degenerate-policy release gate

Six blind-policy ceilings enforced by `scripts/check_degenerate_thresholds.py`:

| Policy | Ceiling |
|---|---|
| `always_abstain` | 0.42 |
| `always_answer_yes` | 0.45 |
| `always_answer_no` | 0.45 |
| `ask_hint_then_abstain` | 0.40 |
| `verify_then_abstain` | 0.45 |
| `verify_then_answer` | 0.55 |

Exit code 0 = all within ceiling; exit code 1 = gate fails. The `always_abstain` ceiling was raised from 0.40 to 0.42 after the Phase 1 formula change (control_score replaced final_policy_score in the 0.20 slot), which inflated the always-abstain score by ~0.01 due to `transition_score = 1.0` for no-second-action episodes.
