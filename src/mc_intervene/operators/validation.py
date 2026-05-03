from __future__ import annotations

from mc_intervene.operators.policy_uncertainty import UncertainPolicyView


def validate_uncertain_policy_view(view: UncertainPolicyView) -> None:
    assert view.world_id
    assert view.prompt_text
    assert view.uncertainty_source
    assert view.uncertainty_operator
    assert view.recoverability_type

    assert view.suggested_optimal_first_action in {
        "answer",
        "ask_hint",
        "verify",
        "abstain",
    }

    assert view.suggested_optimal_final_action in {
        "answer",
        "abstain",
    }

    if view.uncertainty_operator == "hide_threshold":
        assert "base_threshold_days" in view.hidden_fields

    if view.uncertainty_operator == "hide_exception":
        assert "priority_exception_rule" in view.hidden_fields

    if view.uncertainty_operator == "make_rule_ambiguous":
        assert "base_threshold_days" in view.degraded_fields

    if view.uncertainty_operator == "replace_exact_with_approximate":
        assert "days_early" in view.degraded_fields
