from __future__ import annotations

from typing import Any

def derive_optimal_policy(row: dict[str, Any]) -> dict[str, Any]:
    solvability_type = row["solvability_type"]
    hint_effect = row["hint_effect"]
    verify_effect = row["verify_effect"]

    if solvability_type == "solvable_direct":
        if verify_effect in {"weak_confirm", "warn", "ambiguous_support"}:
            return {
                "optimal_first_action": "answer",
                "acceptable_first_actions": ["verify"],
                "optimal_final_action": "answer",
            }
        return {
            "optimal_first_action": "answer",
            "acceptable_first_actions": [],
            "optimal_final_action": "answer",
        }

    if solvability_type == "recoverable_missing":
        if hint_effect == "resolve":
            return {
                "optimal_first_action": "ask_hint",
                "acceptable_first_actions": ["abstain"],
                "optimal_final_action": "answer",
            }
        if hint_effect == "partial":
            return {
                "optimal_first_action": "ask_hint",
                "acceptable_first_actions": ["abstain", "verify"],
                "optimal_final_action": "abstain",
            }
        return {
            "optimal_first_action": "abstain",
            "acceptable_first_actions": ["ask_hint"],
            "optimal_final_action": "abstain",
        }

    if solvability_type == "trap_case":
        if verify_effect in {"confirm", "weak_confirm"}:
            return {
                "optimal_first_action": "verify",
                "acceptable_first_actions": ["answer"],
                "optimal_final_action": "answer",
            }
        if verify_effect == "warn":
            return {
                "optimal_first_action": "verify",
                "acceptable_first_actions": ["answer", "abstain"],
                "optimal_final_action": "answer",
            }
        return {
            "optimal_first_action": "verify",
            "acceptable_first_actions": ["abstain"],
            "optimal_final_action": "abstain",
        }

    if solvability_type == "irrecoverable":
        if hint_effect == "resolve":
            return {
                "optimal_first_action": "ask_hint",
                "acceptable_first_actions": ["abstain"],
                "optimal_final_action": "answer",
            }
        if hint_effect == "partial" and verify_effect in {"warn", "ambiguous_support", "residual_uncertainty"}:
            return {
                "optimal_first_action": "abstain",
                "acceptable_first_actions": ["ask_hint", "verify"],
                "optimal_final_action": "abstain",
            }
        if hint_effect == "partial":
            return {
                "optimal_first_action": "ask_hint",
                "acceptable_first_actions": ["abstain"],
                "optimal_final_action": "abstain",
            }
        return {
            "optimal_first_action": "abstain",
            "acceptable_first_actions": ["ask_hint", "verify"],
            "optimal_final_action": "abstain",
        }

    return {
        "optimal_first_action": "abstain",
        "acceptable_first_actions": [],
        "optimal_final_action": "abstain",
    }