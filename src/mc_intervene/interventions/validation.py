from __future__ import annotations

from mc_intervene.operators.policy_uncertainty import UncertainPolicyView
from mc_intervene.interventions.policy_interventions import PolicyInterventionSpec

_VALID_ACTIONS = {"answer", "ask_hint", "verify", "abstain"}
_VALID_HINT_EFFECTS = {"resolve", "partial", "none"}
_VALID_VERIFY_EFFECTS = {
    "confirm", "weak_confirm", "warn",
    "ambiguous_support", "insufficient", "residual_uncertainty",
}
_VALID_INTERVENTION_VALUES = {"high", "medium", "low", "negative"}


def validate_policy_intervention_spec(
    uncertain_view: UncertainPolicyView,
    spec: PolicyInterventionSpec,
) -> None:
    assert spec.hint_payload
    assert spec.verification_payload
    assert spec.hint_effect in _VALID_HINT_EFFECTS
    assert spec.verify_effect in _VALID_VERIFY_EFFECTS
    assert spec.intervention_value_hint in _VALID_INTERVENTION_VALUES
    assert spec.intervention_value_verify in _VALID_INTERVENTION_VALUES
    assert spec.optimal_first_action in _VALID_ACTIONS
    assert spec.optimal_final_action in {"answer", "abstain"}
    for action in spec.acceptable_first_actions:
        assert action in _VALID_ACTIONS

    # Consistency checks.
    if uncertain_view.uncertainty_operator == "none":
        assert spec.optimal_first_action == "answer"
        assert spec.optimal_final_action == "answer"

    if uncertain_view.uncertainty_operator == "hide_threshold":
        assert spec.hint_effect == "resolve"
        assert spec.intervention_value_hint == "high"
        assert spec.optimal_first_action == "ask_hint"

    if uncertain_view.uncertainty_operator in {"hide_exception", "inject_conflict"}:
        assert spec.intervention_value_verify == "high"
        assert spec.optimal_first_action == "verify"

    if uncertain_view.uncertainty_operator == "make_rule_ambiguous":
        assert spec.optimal_first_action == "abstain"
        assert spec.optimal_final_action == "abstain"

    if uncertain_view.uncertainty_operator in {
        "direct_answerable_hard", "answerable_weak_verify",
    }:
        assert spec.optimal_first_action == "answer"
        assert spec.optimal_final_action == "answer"

    if uncertain_view.uncertainty_operator in {
        "hint_resolves_missing_field", "hint_resolves_exception",
    }:
        assert spec.hint_effect == "resolve"
        assert spec.intervention_value_hint == "high"
        assert spec.optimal_first_action == "ask_hint"

    if uncertain_view.uncertainty_operator == "hint_resolves_exception":
        assert spec.verify_effect == "insufficient"

    if uncertain_view.uncertainty_operator == "irrecoverable_missing_record":
        assert spec.optimal_first_action == "abstain"
        assert spec.optimal_final_action == "abstain"

    if uncertain_view.uncertainty_operator == "verify_residual_uncertainty":
        assert spec.optimal_first_action == "verify"
        assert spec.optimal_final_action == "abstain"
        assert spec.verify_effect == "residual_uncertainty"
        assert spec.intervention_value_verify == "high"
