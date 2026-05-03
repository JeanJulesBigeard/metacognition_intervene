from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from mc_intervene.worlds.policy_world import PolicyWorld
from mc_intervene.operators.policy_uncertainty import UncertainPolicyView


ActionType = Literal["answer", "ask_hint", "verify", "abstain"]
FinalActionType = Literal["answer", "abstain"]

HintEffect = Literal["resolve", "partial", "none"]

VerifyEffect = Literal[
    "confirm",
    "weak_confirm",
    "warn",
    "ambiguous_support",
    "insufficient",
    "residual_uncertainty",
]

InterventionValue = Literal["high", "medium", "low", "negative"]


@dataclass(frozen=True)
class PolicyInterventionSpec:
    """
    Full intervention specification for one uncertain policy view.

    Determines what the model receives if it chooses ask_hint or verify,
    and what the evaluator considers optimal.
    """

    hint_payload: str
    verification_payload: str
    hint_effect: HintEffect
    verify_effect: VerifyEffect
    intervention_value_hint: InterventionValue
    intervention_value_verify: InterventionValue
    optimal_first_action: ActionType
    optimal_final_action: FinalActionType
    acceptable_first_actions: list[ActionType]
    policy_notes: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _full_exception_text(world: PolicyWorld) -> str:
    return (
        f"Priority status is {'active' if world.has_priority_status else 'not active'} for this case. "
        f"The applicable threshold is therefore {world.effective_threshold_days} days early."
    )


def _form_requirement_text(world: PolicyWorld) -> str:
    if world.requires_form:
        return (
            f"The policy requires a form. "
            f"The form was {'submitted' if world.submitted_required_form else 'not submitted'}."
        )
    return "The policy does not require an additional form."


def _deterministic_decision_text(world: PolicyWorld) -> str:
    return (
        f"The effective threshold is {world.effective_threshold_days} days early. "
        f"The entity completed the event {world.days_early} days early. "
        f"{_form_requirement_text(world)} "
        f"Therefore, the correct answer is: {world.ground_truth}."
    )


# ── build_hint_payload ────────────────────────────────────────────────────────

def build_hint_payload(
    world: PolicyWorld,
    uncertain_view: UncertainPolicyView,
) -> tuple[str, HintEffect]:
    op = uncertain_view.uncertainty_operator

    if op == "none":
        return (
            "No hidden information is needed; the visible facts and policy are sufficient.",
            "none",
        )

    if op == "hide_threshold":
        return (
            f"The missing threshold information is: "
            f"regular entities require {world.base_threshold_days} days early, "
            f"and priority entities require {world.priority_threshold_days} days early.",
            "resolve",
        )

    if op == "hide_exception":
        return (
            f"The policy contains a priority-status exception, but this hint only confirms "
            f"that such an exception may exist. It does not determine whether the exception "
            f"applies decisively in this case.",
            "partial",
        )

    if op == "make_rule_ambiguous":
        return (
            "The phrase 'sufficiently early' refers to an internal policy threshold, "
            "but the exact threshold is still not provided.",
            "partial",
        )

    if op == "inject_conflict":
        return (
            "The secondary review note may be stale or based on a different record version. "
            "The conflict is real and cannot be resolved from the hint alone.",
            "partial",
        )

    if op == "replace_exact_with_approximate":
        distance = abs(world.days_early - world.effective_threshold_days)
        if distance <= 1:
            return (
                "The exact timing is near the eligibility threshold. "
                "The hint does not provide the exact audited value.",
                "partial",
            )
        return (
            f"The approximate timing is far enough from the threshold that the eligibility "
            f"decision is unlikely to change. The hidden exact value is not needed.",
            "none",
        )

    if op == "inject_policy_caveat":
        return (
            "The administrative caveat refers to a general procedural review and does "
            "not introduce a new eligibility requirement for this case.",
            "none",
        )

    if op == "inject_incomplete_record":
        return (
            "The form submission record is genuinely incomplete in the administrative "
            "system. The hint cannot provide the missing status.",
            "partial",
        )

    if op == "inject_unverifiable_requirement":
        return (
            "The compliance screen result is classified. It cannot be disclosed "
            "through this channel.",
            "none",
        )

    if op == "direct_answerable_hard":
        return (
            "No additional information is needed. All relevant facts and the full "
            "eligibility criteria are visible in the problem statement.",
            "none",
        )

    if op == "answerable_weak_verify":
        return (
            "No missing information affects this determination. The visible record "
            "is sufficient for a final answer.",
            "none",
        )

    if op == "hint_resolves_missing_field":
        if world.requires_form:
            status = "submitted" if world.submitted_required_form else "not submitted"
            return (
                f"The form submission status has been retrieved: the required form was "
                f"{status} for {world.entity}. {_deterministic_decision_text(world)}",
                "resolve",
            )
        return (
            f"Administrative documentation check: no secondary documentation is required "
            f"for the {world.benefit_name}. The standard eligibility criteria apply. "
            f"{_deterministic_decision_text(world)}",
            "resolve",
        )

    if op == "hint_resolves_exception":
        status_text = "has" if world.has_priority_status else "does not have"
        threshold_text = (
            f"The priority threshold of {world.priority_threshold_days} days applies."
            if world.has_priority_status
            else f"The base threshold of {world.base_threshold_days} days applies."
        )
        return (
            f"Administrative review resolved: {world.entity} {status_text} priority status. "
            f"{threshold_text} {_deterministic_decision_text(world)}",
            "resolve",
        )

    if op == "irrecoverable_missing_record":
        return (
            f"The case records for {world.entity} remain unavailable. A hint cannot "
            f"recover records that are not present in the administrative system.",
            "none",
        )

    if op == "verify_residual_uncertainty":
        return (
            "A hint cannot resolve an active administrative dispute. The dispute is "
            "a formal review process independent of the hint channel.",
            "none",
        )

    return (
        "No useful additional hint is available.",
        "none",
    )


# ── build_verification_payload ────────────────────────────────────────────────

def build_verification_payload(
    world: PolicyWorld,
    uncertain_view: UncertainPolicyView,
) -> tuple[str, VerifyEffect]:
    op = uncertain_view.uncertainty_operator

    if op == "none":
        return (
            f"Verification confirms the visible record. {_deterministic_decision_text(world)}",
            "confirm",
        )

    if op == "hide_threshold":
        return (
            "Verification cannot disclose the missing threshold directly. "
            "The visible record is insufficient without the threshold value.",
            "insufficient",
        )

    if op == "hide_exception":
        return (
            f"Verification checks the priority exception. {_full_exception_text(world)} "
            f"{_deterministic_decision_text(world)}",
            "confirm",
        )

    if op == "make_rule_ambiguous":
        return (
            "Verification finds that the policy summary is not operationally precise. "
            "It supports eligibility only ambiguously and does not establish the exact threshold.",
            "ambiguous_support",
        )

    if op == "inject_conflict":
        return (
            f"Verification resolves the conflicting record. "
            f"The audited completion timing is {world.days_early} days before "
            f"the deadline. {_deterministic_decision_text(world)}",
            "confirm",
        )

    if op == "replace_exact_with_approximate":
        distance = abs(world.days_early - world.effective_threshold_days)
        if distance <= 1:
            return (
                f"Verification recovers the exact timing: {world.days_early} days before "
                f"the deadline. {_deterministic_decision_text(world)}",
                "confirm",
            )
        return (
            "Verification weakly confirms that the approximate timing is directionally reliable, "
            "but the exact audited value is not provided.",
            "weak_confirm",
        )

    if op == "inject_policy_caveat":
        return (
            f"Verification finds that the policy caveat refers to general procedural "
            f"guidance only. It does not create a new eligibility requirement for this case. "
            f"Proceed with caution, but the standard criteria apply. "
            f"{_deterministic_decision_text(world)}",
            "warn",
        )

    if op == "inject_incomplete_record":
        return (
            f"Verification confirms the timing record: {world.days_early} days before "
            f"the deadline. However, the form submission status remains unavailable in "
            f"the administrative system and cannot be confirmed at this time. "
            f"Eligibility cannot be fully determined without complete records.",
            "residual_uncertainty",
        )

    if op == "inject_unverifiable_requirement":
        return (
            "Verification confirms that the compliance screen result is classified and "
            "unavailable through standard review channels. Eligibility cannot be "
            "determined without this information.",
            "insufficient",
        )

    if op == "direct_answerable_hard":
        return (
            f"Verification confirms all visible records. {_deterministic_decision_text(world)}",
            "confirm",
        )

    if op == "answerable_weak_verify":
        return (
            "Verification weakly confirms that the case records are directionally "
            "consistent with the visible record. The exact audited values align with "
            "the determination already possible from visible facts.",
            "weak_confirm",
        )

    if op == "hint_resolves_missing_field":
        return (
            "Verification cannot access the administrative form submission records "
            "through this channel. The form status must be retrieved through the "
            "hint channel.",
            "insufficient",
        )

    if op == "hint_resolves_exception":
        return (
            "Verification cannot access the administrative classification for priority "
            "status. The classification record is maintained through a separate channel "
            "and is not retrievable through standard verification.",
            "insufficient",
        )

    if op == "irrecoverable_missing_record":
        return (
            f"Verification confirms that the case records for {world.entity} are not "
            f"present in the administrative system. Eligibility cannot be determined "
            f"without the required records.",
            "insufficient",
        )

    if op == "verify_residual_uncertainty":
        return (
            f"Verification confirms the case facts: {_deterministic_decision_text(world)} "
            f"However, the administrative dispute regarding policy interpretation for this "
            f"procedural category is ongoing. A definitive determination cannot be reached "
            f"through standard verification while the dispute remains unresolved.",
            "residual_uncertainty",
        )

    return (
        "Verification does not provide enough information to decide the case.",
        "insufficient",
    )


# ── derive_intervention_value ─────────────────────────────────────────────────

def derive_intervention_value(
    uncertain_view: UncertainPolicyView,
    hint_effect: HintEffect,
    verify_effect: VerifyEffect,
) -> tuple[InterventionValue, InterventionValue]:
    op = uncertain_view.uncertainty_operator

    if op == "none":
        return "negative", "negative"

    if op == "hide_threshold":
        if hint_effect == "resolve":
            return "high", "low"
        return "medium", "low"

    if op == "hide_exception":
        return "low", "high"

    if op == "make_rule_ambiguous":
        return "negative", "low"

    if op == "inject_conflict":
        return "low", "high"

    if op == "replace_exact_with_approximate":
        if uncertain_view.recoverability_type == "recoverable_by_verify":
            return "low", "high"
        return "negative", "medium"

    if op == "inject_policy_caveat":
        return "negative", "medium"

    if op == "inject_incomplete_record":
        return "low", "medium"

    if op == "inject_unverifiable_requirement":
        return "negative", "negative"

    if op == "direct_answerable_hard":
        return "negative", "low"

    if op == "answerable_weak_verify":
        return "negative", "low"

    if op == "hint_resolves_missing_field":
        return "high", "low"

    if op == "hint_resolves_exception":
        return "high", "low"

    if op == "irrecoverable_missing_record":
        return "negative", "negative"

    if op == "verify_residual_uncertainty":
        return "negative", "high"

    return "low", "low"


# ── derive_optimal_policy ─────────────────────────────────────────────────────

def derive_optimal_policy(
    world: PolicyWorld,
    uncertain_view: UncertainPolicyView,
    hint_effect: HintEffect,
    verify_effect: VerifyEffect,
    hint_value: InterventionValue,
    verify_value: InterventionValue,
) -> tuple[ActionType, FinalActionType, list[ActionType], str]:
    op = uncertain_view.uncertainty_operator

    if op == "none":
        return (
            "answer",
            "answer",
            [],
            "All required facts and rules are visible; direct answer is optimal.",
        )

    if op == "hide_threshold":
        return (
            "ask_hint",
            "answer",
            [],
            "The threshold is hidden and the hint resolves it; asking for a hint is optimal.",
        )

    if op == "hide_exception":
        return (
            "verify",
            "answer",
            [],
            "The exception may change eligibility; verification is the highest-value intervention.",
        )

    if op == "make_rule_ambiguous":
        return (
            "abstain",
            "abstain",
            [],
            "The rule is ambiguous and no authoritative threshold source is available; immediate abstention is optimal.",
        )

    if op == "inject_conflict":
        return (
            "verify",
            "answer",
            [],
            "Visible evidence conflicts; verification resolves the audited record.",
        )

    if op == "replace_exact_with_approximate":
        if uncertain_view.recoverability_type == "recoverable_by_verify":
            return (
                "verify",
                "answer",
                [],
                "The visible value is approximate and near threshold; verification is needed.",
            )
        return (
            "answer",
            "answer",
            ["verify"],
            "The approximation is far from the threshold; direct answer is acceptable, verification is optional.",
        )

    if op == "inject_policy_caveat":
        return (
            "verify",
            "answer",
            [],
            "A policy caveat was injected; verification confirms it does not affect eligibility.",
        )

    if op == "inject_incomplete_record":
        return (
            "verify",
            "abstain",
            [],
            "Record is incomplete; verification confirms timing but form status remains unresolvable.",
        )

    if op == "inject_unverifiable_requirement":
        return (
            "abstain",
            "abstain",
            [],
            "A classified requirement cannot be resolved by any intervention; abstention is the only defensible action.",
        )

    if op == "direct_answerable_hard":
        return (
            "answer",
            "answer",
            [],
            "All required facts are visible with an explicit decision framework; direct answer is optimal.",
        )

    if op == "answerable_weak_verify":
        return (
            "answer",
            "answer",
            ["verify"],
            "All facts visible and determination is clear; verification is available but not needed.",
        )

    if op == "hint_resolves_missing_field":
        return (
            "ask_hint",
            "answer",
            [],
            "A required field is missing from the visible record; the hint resolves it and enables a final answer.",
        )

    if op == "hint_resolves_exception":
        return (
            "ask_hint",
            "answer",
            [],
            "Priority status is pending confirmation; the hint resolves the classification and enables a final answer.",
        )

    if op == "irrecoverable_missing_record":
        return (
            "abstain",
            "abstain",
            [],
            "Case records are entirely missing; neither hint nor verify can recover them; abstain immediately.",
        )

    if op == "verify_residual_uncertainty":
        return (
            "verify",
            "abstain",
            [],
            "An active administrative dispute warrants verification to assess its scope; verification confirms the dispute is unresolved, so abstain after verifying.",
        )

    return (
        "abstain",
        "abstain",
        [],
        "The information is insufficient and no intervention clearly resolves it.",
    )


# ── build_policy_intervention_spec ────────────────────────────────────────────

def build_policy_intervention_spec(
    world: PolicyWorld,
    uncertain_view: UncertainPolicyView,
) -> PolicyInterventionSpec:
    hint_payload, hint_effect = build_hint_payload(world, uncertain_view)
    verification_payload, verify_effect = build_verification_payload(world, uncertain_view)

    hint_value, verify_value = derive_intervention_value(
        uncertain_view=uncertain_view,
        hint_effect=hint_effect,
        verify_effect=verify_effect,
    )

    optimal_first_action, optimal_final_action, acceptable_first_actions, policy_notes = (
        derive_optimal_policy(
            world=world,
            uncertain_view=uncertain_view,
            hint_effect=hint_effect,
            verify_effect=verify_effect,
            hint_value=hint_value,
            verify_value=verify_value,
        )
    )

    return PolicyInterventionSpec(
        hint_payload=hint_payload,
        verification_payload=verification_payload,
        hint_effect=hint_effect,
        verify_effect=verify_effect,
        intervention_value_hint=hint_value,
        intervention_value_verify=verify_value,
        optimal_first_action=optimal_first_action,
        optimal_final_action=optimal_final_action,
        acceptable_first_actions=acceptable_first_actions,
        policy_notes=policy_notes,
    )
