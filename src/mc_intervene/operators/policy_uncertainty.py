from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Literal

from mc_intervene.worlds.policy_world import PolicyWorld
from mc_intervene.renderers.policy_renderers import RenderedPolicyView


UncertaintySource = Literal[
    "none",
    "missing_threshold",
    "hidden_exception",
    "ambiguous_rule",
    "conflicting_evidence",
    "approximate_value",
    "policy_caveat",
    "incomplete_record",
    "unverifiable_requirement",
    "multi_step_reasoning",
    "weak_verify_available",
    "missing_form_field",
    "exception_hint_only",
    "missing_case_record",
    "administrative_dispute",
]

UncertaintyOperator = Literal[
    "none",
    "hide_threshold",
    "hide_exception",
    "make_rule_ambiguous",
    "inject_conflict",
    "replace_exact_with_approximate",
    "inject_policy_caveat",
    "inject_incomplete_record",
    "inject_unverifiable_requirement",
    "direct_answerable_hard",
    "answerable_weak_verify",
    "hint_resolves_missing_field",
    "hint_resolves_exception",
    "irrecoverable_missing_record",
    "verify_residual_uncertainty",
]

RecoverabilityType = Literal[
    "fully_observable",
    "recoverable_by_hint",
    "recoverable_by_verify",
    "partially_recoverable",
    "irrecoverable",
]

PolicyOperatorName = Literal[
    "none",
    "hide_threshold",
    "hide_exception",
    "make_rule_ambiguous",
    "inject_conflict",
    "replace_exact_with_approximate",
    "inject_policy_caveat",
    "inject_incomplete_record",
    "inject_unverifiable_requirement",
    "direct_answerable_hard",
    "answerable_weak_verify",
    "hint_resolves_missing_field",
    "hint_resolves_exception",
    "irrecoverable_missing_record",
    "verify_residual_uncertainty",
]


@dataclass(frozen=True)
class UncertainPolicyView:
    """
    A rendered view after an uncertainty operator has been applied.

    This is still not a final benchmark row. It is the bridge between:
    - hidden world generation
    - public prompt construction
    - intervention/policy derivation
    """

    world_id: str
    view_type: str
    prompt_text: str

    uncertainty_source: UncertaintySource
    uncertainty_operator: UncertaintyOperator
    recoverability_type: RecoverabilityType

    # Fields hidden from the prompt but known to the generator.
    hidden_fields: list[str] = field(default_factory=list)

    # Fields made vague, approximate, or unreliable.
    degraded_fields: list[str] = field(default_factory=list)

    # Notes for validation/debugging, not shown to model.
    operator_notes: str = ""

    # Preserve useful metadata from the source renderer.
    visible_facts: dict[str, str] = field(default_factory=dict)
    visible_policy_parts: dict[str, str] = field(default_factory=dict)
    evidence_fragments: list[str] = field(default_factory=list)

    # Suggested intervention semantics for Step 4.
    suggested_hint_effect: str = "none"
    suggested_verify_effect: str = "insufficient"

    # Not final labels yet, but useful hints for policy derivation.
    suggested_optimal_first_action: str = "abstain"
    suggested_optimal_final_action: str = "abstain"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _replace_many(text: str, replacements: dict[str, str]) -> str:
    out = text
    for old, new in replacements.items():
        out = out.replace(old, new)
    return out


def _copy_visible_facts(view: RenderedPolicyView) -> dict[str, str]:
    return dict(view.visible_facts)


def _copy_visible_policy_parts(view: RenderedPolicyView) -> dict[str, str]:
    return dict(view.visible_policy_parts)


def _copy_fragments(view: RenderedPolicyView) -> list[str]:
    return list(view.evidence_fragments)


def _base_uncertain_view(
    world: PolicyWorld,
    view: RenderedPolicyView,
    prompt_text: str,
    uncertainty_source: UncertaintySource,
    uncertainty_operator: UncertaintyOperator,
    recoverability_type: RecoverabilityType,
    hidden_fields: list[str] | None = None,
    degraded_fields: list[str] | None = None,
    operator_notes: str = "",
    suggested_hint_effect: str = "none",
    suggested_verify_effect: str = "insufficient",
    suggested_optimal_first_action: str = "abstain",
    suggested_optimal_final_action: str = "abstain",
) -> UncertainPolicyView:
    return UncertainPolicyView(
        world_id=world.world_id,
        view_type=view.view_type,
        prompt_text=prompt_text,
        uncertainty_source=uncertainty_source,
        uncertainty_operator=uncertainty_operator,
        recoverability_type=recoverability_type,
        hidden_fields=hidden_fields or [],
        degraded_fields=degraded_fields or [],
        operator_notes=operator_notes,
        visible_facts=_copy_visible_facts(view),
        visible_policy_parts=_copy_visible_policy_parts(view),
        evidence_fragments=_copy_fragments(view),
        suggested_hint_effect=suggested_hint_effect,
        suggested_verify_effect=suggested_verify_effect,
        suggested_optimal_first_action=suggested_optimal_first_action,
        suggested_optimal_final_action=suggested_optimal_final_action,
    )


# ── Existing operators ────────────────────────────────────────────────────────

def no_uncertainty(world: PolicyWorld, view: RenderedPolicyView) -> UncertainPolicyView:
    return _base_uncertain_view(
        world=world,
        view=view,
        prompt_text=view.prompt_text,
        uncertainty_source="none",
        uncertainty_operator="none",
        recoverability_type="fully_observable",
        hidden_fields=[],
        degraded_fields=[],
        operator_notes="All required facts and policy rules are visible.",
        suggested_hint_effect="none",
        suggested_verify_effect="confirm",
        suggested_optimal_first_action="answer",
        suggested_optimal_final_action="answer",
    )


def hide_threshold(world: PolicyWorld, view: RenderedPolicyView) -> UncertainPolicyView:
    # If form is required and not submitted, the answer is "no" regardless of threshold.
    # Hiding the threshold would not create genuine uncertainty.
    if world.requires_form and not world.submitted_required_form:
        return no_uncertainty(world, view)

    replacements = {
        f"at least {world.base_threshold_days} days": "at least an unspecified number of days",
        # Note: do NOT add a bare "{N} days before" pattern here — it collides with the
        # entity timing text "{days_early} days before the deadline" when days_early == base_threshold_days.
        f"Regular threshold | {world.base_threshold_days} days": "Regular threshold | not disclosed",
        f"Regular entities require at least {world.base_threshold_days} days early.": (
            "Regular entities require completing the event sufficiently early, "
            "but the exact threshold is not disclosed."
        ),
        f"regular entities need to complete the {world.event_name} at least {world.base_threshold_days} days early": (
            f"regular entities need to complete the {world.event_name} sufficiently early"
        ),
    }
    prompt = _replace_many(view.prompt_text, replacements)

    replacements_2 = {
        f"Priority entities only need {world.priority_threshold_days} days early.": (
            "Priority entities may qualify under a different threshold, but the exact value is not shown."
        ),
        f"Priority entities qualify if they complete it at least {world.priority_threshold_days} days before the deadline.": (
            "Priority entities may qualify under a different threshold, but the exact value is not shown."
        ),
        f"Priority entities require at least {world.priority_threshold_days} days early.": (
            "Priority entities require a different early-completion threshold, but it is not disclosed."
        ),
        f"Priority threshold | {world.priority_threshold_days} days": "Priority threshold | not disclosed",
    }
    prompt = _replace_many(prompt, replacements_2)

    return _base_uncertain_view(
        world=world,
        view=view,
        prompt_text=prompt,
        uncertainty_source="missing_threshold",
        uncertainty_operator="hide_threshold",
        recoverability_type="recoverable_by_hint",
        hidden_fields=["base_threshold_days", "priority_threshold_days"],
        degraded_fields=[],
        operator_notes="The exact eligibility threshold is hidden. A hint can reveal the threshold.",
        suggested_hint_effect="resolve",
        suggested_verify_effect="insufficient",
        suggested_optimal_first_action="ask_hint",
        suggested_optimal_final_action="answer",
    )


def hide_exception(world: PolicyWorld, view: RenderedPolicyView) -> UncertainPolicyView:
    replacements = {
        f"Priority entities only need {world.priority_threshold_days} days early.": (
            "Some priority entities may qualify under an exception, but the exception details are not shown."
        ),
        f"Priority entities qualify if they complete it at least {world.priority_threshold_days} days before the deadline.": (
            "Priority entities may qualify under an exception, but the exception details are not shown."
        ),
        f"Priority entities require at least {world.priority_threshold_days} days early.": (
            "Priority entities may have an exception, but the exact exception threshold is not shown."
        ),
        f"| Priority threshold | {world.priority_threshold_days} days |": (
            "| Priority threshold | exception exists but exact threshold not disclosed |"
        ),
    }
    prompt = _replace_many(view.prompt_text, replacements)

    if "priority" not in prompt.lower():
        prompt += (
            "\n\nNote: The policy may contain an exception for priority-status entities, "
            "but the exact exception is not included in the visible record."
        )

    return _base_uncertain_view(
        world=world,
        view=view,
        prompt_text=prompt,
        uncertainty_source="hidden_exception",
        uncertainty_operator="hide_exception",
        recoverability_type="recoverable_by_verify",
        hidden_fields=["priority_threshold_days", "priority_exception_rule"],
        degraded_fields=[],
        operator_notes=(
            "The priority exception is hidden. Verification can determine whether the exception applies."
        ),
        suggested_hint_effect="partial",
        suggested_verify_effect="confirm" if world.has_priority_status else "warn",
        suggested_optimal_first_action="verify",
        suggested_optimal_final_action="answer",
    )


def make_rule_ambiguous(world: PolicyWorld, view: RenderedPolicyView) -> UncertainPolicyView:
    replacements = {
        f"at least {world.base_threshold_days} days before the deadline": (
            "sufficiently before the deadline"
        ),
        f"at least {world.base_threshold_days} days early": (
            "sufficiently early"
        ),
        f"at least {world.priority_threshold_days} days before the deadline": (
            "sufficiently early for priority entities"
        ),
        f"{world.base_threshold_days} days": "a sufficient number of days",
        f"{world.priority_threshold_days} days": "a reduced number of days",
    }
    prompt = _replace_many(view.prompt_text, replacements)
    prompt += (
        "\n\nThe visible policy summary does not define exactly what "
        "'sufficiently early' means, and no authoritative threshold document "
        "is available in the current system. The policy wording alone is "
        "insufficient to make a deterministic eligibility decision."
    )

    return _base_uncertain_view(
        world=world,
        view=view,
        prompt_text=prompt,
        uncertainty_source="ambiguous_rule",
        uncertainty_operator="make_rule_ambiguous",
        recoverability_type="irrecoverable",
        hidden_fields=[],
        degraded_fields=["base_threshold_days", "priority_threshold_days"],
        operator_notes=(
            "Exact thresholds replaced by vague language. No authoritative source available. "
            "Immediate abstention is optimal — the ambiguity cannot be resolved by any intervention."
        ),
        suggested_hint_effect="partial",
        suggested_verify_effect="ambiguous_support",
        suggested_optimal_first_action="abstain",
        suggested_optimal_final_action="abstain",
    )


def inject_conflict(world: PolicyWorld, view: RenderedPolicyView) -> UncertainPolicyView:
    conflicting_days = world.days_early + 2
    if conflicting_days == world.days_early:
        conflicting_days += 1

    conflict_fragment = (
        f"Conflicting evidence — Secondary review note:\n"
        f"A separate reviewer recorded {world.entity} as completing the "
        f"{world.event_name} {conflicting_days} days before the deadline."
    )

    prompt = (
        f"{view.prompt_text}\n\n"
        f"{conflict_fragment}\n\n"
        f"The visible record contains conflicting completion timing. "
        f"Use caution before deciding eligibility."
    )

    fragments = _copy_fragments(view)
    fragments.append(conflict_fragment)

    base = _base_uncertain_view(
        world=world,
        view=view,
        prompt_text=prompt,
        uncertainty_source="conflicting_evidence",
        uncertainty_operator="inject_conflict",
        recoverability_type="recoverable_by_verify",
        hidden_fields=[],
        degraded_fields=["days_early"],
        operator_notes=(
            f"Injected conflicting completion timing: original={world.days_early}, "
            f"conflict={conflicting_days}."
        ),
        suggested_hint_effect="partial",
        suggested_verify_effect="confirm",
        suggested_optimal_first_action="verify",
        suggested_optimal_final_action="answer",
    )

    return dataclasses.replace(base, evidence_fragments=fragments)


def replace_exact_with_approximate(world: PolicyWorld, view: RenderedPolicyView) -> UncertainPolicyView:
    replacements = {
        f"{world.days_early} days before the deadline": (
            f"about {world.days_early} days before the deadline"
        ),
        f"Completed: {world.days_early} days before the deadline": (
            f"Completed: about {world.days_early} days before the deadline"
        ),
        f"| Days before deadline | {world.days_early} |": (
            f"| Days before deadline | about {world.days_early} |"
        ),
    }
    prompt = _replace_many(view.prompt_text, replacements)
    prompt += "\n\nThe visible timing record is approximate rather than exact."

    distance_to_threshold = abs(world.days_early - world.effective_threshold_days)

    if distance_to_threshold <= 1:
        recoverability_type: RecoverabilityType = "recoverable_by_verify"
        suggested_first = "verify"
        suggested_final = "answer"
        suggested_verify = "confirm"
    else:
        recoverability_type = "partially_recoverable"
        suggested_first = "answer"
        suggested_final = "answer"
        suggested_verify = "weak_confirm"

    return _base_uncertain_view(
        world=world,
        view=view,
        prompt_text=prompt,
        uncertainty_source="approximate_value",
        uncertainty_operator="replace_exact_with_approximate",
        recoverability_type=recoverability_type,
        hidden_fields=[],
        degraded_fields=["days_early"],
        operator_notes=(
            f"Exact days_early={world.days_early} was replaced by approximate wording. "
            f"Distance to threshold={distance_to_threshold}."
        ),
        suggested_hint_effect="none",
        suggested_verify_effect=suggested_verify,
        suggested_optimal_first_action=suggested_first,
        suggested_optimal_final_action=suggested_final,
    )


def inject_unverifiable_requirement(world: PolicyWorld, view: RenderedPolicyView) -> UncertainPolicyView:
    prompt = (
        f"{view.prompt_text}\n\n"
        f"Additional eligibility note: Qualification for the {world.benefit_name} "
        f"may also depend on the outcome of a confidential compliance screen. "
        f"The result of this screen is not accessible in the visible record and "
        f"cannot be retrieved through standard review channels."
    )

    return _base_uncertain_view(
        world=world,
        view=view,
        prompt_text=prompt,
        uncertainty_source="unverifiable_requirement",
        uncertainty_operator="inject_unverifiable_requirement",
        recoverability_type="irrecoverable",
        hidden_fields=["compliance_screen_result"],
        degraded_fields=[],
        operator_notes=(
            "A classified compliance requirement was injected. Neither hint nor "
            "verification can resolve it. Abstention is the only defensible action."
        ),
        suggested_hint_effect="none",
        suggested_verify_effect="insufficient",
        suggested_optimal_first_action="abstain",
        suggested_optimal_final_action="abstain",
    )


def inject_policy_caveat(world: PolicyWorld, view: RenderedPolicyView) -> UncertainPolicyView:
    caveat_text = (
        "\n\nAdministrative note: This benefit's policy is subject to a pending "
        "procedural review. A policy caveat may apply to cases like this one. "
        "Verify eligibility carefully before finalising."
    )
    prompt = view.prompt_text + caveat_text

    return _base_uncertain_view(
        world=world,
        view=view,
        prompt_text=prompt,
        uncertainty_source="policy_caveat",
        uncertainty_operator="inject_policy_caveat",
        recoverability_type="recoverable_by_verify",
        hidden_fields=[],
        degraded_fields=["policy_applicability"],
        operator_notes=(
            "A procedural caveat was injected. Verification confirms the caveat is "
            "general and does not affect this case's eligibility outcome."
        ),
        suggested_hint_effect="none",
        suggested_verify_effect="warn",
        suggested_optimal_first_action="verify",
        suggested_optimal_final_action="answer",
    )


def inject_incomplete_record(world: PolicyWorld, view: RenderedPolicyView) -> UncertainPolicyView:
    replacements = {
        "Required form submitted: yes": "Required form submitted: pending verification",
        "Required form submitted: no": "Required form submitted: pending verification",
        f"{world.entity} submitted the required form.": (
            f"The form submission status for {world.entity} is pending verification."
        ),
        f"{world.entity} did not submit the required form.": (
            f"The form submission status for {world.entity} is pending verification."
        ),
        "| Required form submitted | yes |": "| Required form submitted | pending |",
        "| Required form submitted | no |": "| Required form submitted | pending |",
    }
    prompt = _replace_many(view.prompt_text, replacements)
    prompt += (
        "\n\nNote: The form submission record could not be retrieved from the "
        "administrative system at this time."
    )

    return _base_uncertain_view(
        world=world,
        view=view,
        prompt_text=prompt,
        uncertainty_source="incomplete_record",
        uncertainty_operator="inject_incomplete_record",
        recoverability_type="irrecoverable",
        hidden_fields=["submitted_required_form"],
        degraded_fields=[],
        operator_notes=(
            "Form submission status was hidden. Verification can confirm timing "
            "but not form status, leaving residual uncertainty."
        ),
        suggested_hint_effect="partial",
        suggested_verify_effect="residual_uncertainty",
        suggested_optimal_first_action="verify",
        suggested_optimal_final_action="abstain",
    )


# ── New operators ─────────────────────────────────────────────────────────────

def direct_answerable_hard(world: PolicyWorld, view: RenderedPolicyView) -> UncertainPolicyView:
    extra = (
        f"\n\nEligibility analysis notes:\n"
        f"Step 1 — Identify the applicable threshold:\n"
        f"  • Regular entities: must complete the event at least "
        f"{world.base_threshold_days} days early.\n"
        f"  • Priority entities: must complete the event at least "
        f"{world.priority_threshold_days} days early.\n"
        f"  • This entity's priority status is visible above.\n"
        f"Step 2 — Compare the entity's completion timing to the applicable threshold.\n"
        f"{'Step 3 — Confirm whether the required form was submitted.' if world.requires_form else 'Step 3 — No additional form is required for this benefit.'}\n"
        f"All required facts are present in the visible record."
    )
    prompt = view.prompt_text + extra

    return _base_uncertain_view(
        world=world,
        view=view,
        prompt_text=prompt,
        uncertainty_source="multi_step_reasoning",
        uncertainty_operator="direct_answerable_hard",
        recoverability_type="fully_observable",
        hidden_fields=[],
        degraded_fields=[],
        operator_notes=(
            "All facts visible; multi-step analysis framework added. "
            "Challenge is reasoning complexity, not information availability."
        ),
        suggested_hint_effect="none",
        suggested_verify_effect="confirm",
        suggested_optimal_first_action="answer",
        suggested_optimal_final_action="answer",
    )


def answerable_weak_verify(world: PolicyWorld, view: RenderedPolicyView) -> UncertainPolicyView:
    prompt = (
        view.prompt_text
        + "\n\nNote: An independent case verification is available on request if needed, "
        "though the visible record contains all facts required for a determination."
    )

    return _base_uncertain_view(
        world=world,
        view=view,
        prompt_text=prompt,
        uncertainty_source="weak_verify_available",
        uncertainty_operator="answerable_weak_verify",
        recoverability_type="fully_observable",
        hidden_fields=[],
        degraded_fields=[],
        operator_notes=(
            "All facts visible; verification is available but not needed. "
            "Optimal action is to answer directly."
        ),
        suggested_hint_effect="none",
        suggested_verify_effect="weak_confirm",
        suggested_optimal_first_action="answer",
        suggested_optimal_final_action="answer",
    )


def hint_resolves_missing_field(world: PolicyWorld, view: RenderedPolicyView) -> UncertainPolicyView:
    # Form must be required AND timing must already pass for form status to be decisive.
    # If no form is needed, nothing is missing. If timing already fails, form doesn't matter.
    if not world.requires_form or world.days_early < world.effective_threshold_days:
        return no_uncertainty(world, view)

    if world.requires_form:
        replacements = {
            "Required form submitted: yes": "Required form submitted: status unknown",
            "Required form submitted: no": "Required form submitted: status unknown",
            f"{world.entity} submitted the required form.": (
                f"The form submission status for {world.entity} is not available in the current record."
            ),
            f"{world.entity} did not submit the required form.": (
                f"The form submission status for {world.entity} is not available in the current record."
            ),
            "| Required form submitted | yes |": "| Required form submitted | unknown |",
            "| Required form submitted | no |": "| Required form submitted | unknown |",
        }
        prompt = _replace_many(view.prompt_text, replacements)
        prompt += (
            "\n\nNote: This benefit requires a form submission. "
            "The form submission status is not available in the current record view. "
            "A hint can retrieve the current administrative record on file."
        )
        hidden_fields = ["submitted_required_form"]
        operator_notes = "Form submission status hidden; hint resolves it to a deterministic answer."
    else:
        prompt = (
            view.prompt_text
            + "\n\nAdministrative note: The processing office requires confirmation "
            "of secondary documentation status before finalising this determination. "
            "A hint can retrieve the documentation status from the administrative record."
        )
        hidden_fields = []
        operator_notes = (
            "requires_form=False; hint confirms no secondary documentation is required."
        )

    return _base_uncertain_view(
        world=world,
        view=view,
        prompt_text=prompt,
        uncertainty_source="missing_form_field",
        uncertainty_operator="hint_resolves_missing_field",
        recoverability_type="recoverable_by_hint",
        hidden_fields=hidden_fields,
        degraded_fields=[],
        operator_notes=operator_notes,
        suggested_hint_effect="resolve",
        suggested_verify_effect="insufficient",
        suggested_optimal_first_action="ask_hint",
        suggested_optimal_final_action="answer",
    )


def hint_resolves_exception(world: PolicyWorld, view: RenderedPolicyView) -> UncertainPolicyView:
    # Priority status must actually change the eligibility outcome to create genuine uncertainty.
    # Check both branches: if form fails the answer is "no" regardless; if timing passes under
    # both thresholds (or fails under both) priority status is irrelevant.
    form_ok = (not world.requires_form) or world.submitted_required_form
    if not form_ok:
        return no_uncertainty(world, view)
    passes_as_priority = world.days_early >= world.priority_threshold_days
    passes_as_regular = world.days_early >= world.base_threshold_days
    if passes_as_priority == passes_as_regular:
        return no_uncertainty(world, view)

    status_val = "yes" if world.has_priority_status else "no"
    active_val = "active" if world.has_priority_status else "not active"

    replacements = {
        f"{world.entity} has priority status.": (
            f"The priority status classification for {world.entity} is pending administrative confirmation."
        ),
        f"{world.entity} does not have priority status.": (
            f"The priority status classification for {world.entity} is pending administrative confirmation."
        ),
        f"- Priority status: {status_val}": "- Priority status: pending confirmation",
        f"Priority status: {active_val}.": "Priority status: pending administrative confirmation.",
        f"| Priority status | {status_val} |": "| Priority status | pending confirmation |",
    }
    prompt = _replace_many(view.prompt_text, replacements)
    prompt += (
        "\n\nNote: Priority status classification determines which eligibility threshold applies. "
        "The classification is under administrative review and has not been confirmed in the visible record. "
        "A hint can retrieve the current classification on file."
    )

    return _base_uncertain_view(
        world=world,
        view=view,
        prompt_text=prompt,
        uncertainty_source="exception_hint_only",
        uncertainty_operator="hint_resolves_exception",
        recoverability_type="recoverable_by_hint",
        hidden_fields=["has_priority_status"],
        degraded_fields=[],
        operator_notes=(
            "Priority status hidden (marked as pending confirmation). "
            "Hint resolves it; verification cannot access the classification channel."
        ),
        suggested_hint_effect="resolve",
        suggested_verify_effect="insufficient",
        suggested_optimal_first_action="ask_hint",
        suggested_optimal_final_action="answer",
    )


def irrecoverable_missing_record(world: PolicyWorld, view: RenderedPolicyView) -> UncertainPolicyView:
    prompt = (
        f"Policy: {world.full_policy_text}\n\n"
        f"Case: An eligibility determination has been requested for {world.entity} "
        f"seeking the {world.benefit_name}.\n\n"
        f"Record status: The administrative records for this case — including completion "
        f"timing, priority status classification, and documentation status — are currently "
        f"unavailable in the system. They may have been archived, transferred to a "
        f"different administrative unit, or not yet entered into the current system.\n\n"
        f"Question: Did {world.entity} qualify for the {world.benefit_name}?"
    )

    return _base_uncertain_view(
        world=world,
        view=view,
        prompt_text=prompt,
        uncertainty_source="missing_case_record",
        uncertainty_operator="irrecoverable_missing_record",
        recoverability_type="irrecoverable",
        hidden_fields=["days_early", "has_priority_status", "submitted_required_form"],
        degraded_fields=[],
        operator_notes=(
            "All case facts hidden; only policy is visible. "
            "Neither hint nor verify can recover missing records. Abstain immediately."
        ),
        suggested_hint_effect="none",
        suggested_verify_effect="insufficient",
        suggested_optimal_first_action="abstain",
        suggested_optimal_final_action="abstain",
    )


def verify_residual_uncertainty(world: PolicyWorld, view: RenderedPolicyView) -> UncertainPolicyView:
    prompt = (
        view.prompt_text
        + f"\n\nAdministrative dispute note: The eligibility determination for this "
        f"case is currently under active administrative dispute. A formal review body "
        f"has raised unresolved questions about how the {world.benefit_name} policy "
        f"applies to entities in {world.entity}'s procedural category. "
        f"The dispute is independent of the standard timing and documentation criteria "
        f"visible above and cannot be resolved through standard review channels."
    )

    return _base_uncertain_view(
        world=world,
        view=view,
        prompt_text=prompt,
        uncertainty_source="administrative_dispute",
        uncertainty_operator="verify_residual_uncertainty",
        recoverability_type="partially_recoverable",
        hidden_fields=[],
        degraded_fields=["policy_applicability"],
        operator_notes=(
            "An administrative dispute was injected. The model should verify to assess "
            "whether the dispute can be resolved; verification returns residual_uncertainty, "
            "so the correct final action is abstain."
        ),
        suggested_hint_effect="none",
        suggested_verify_effect="residual_uncertainty",
        suggested_optimal_first_action="verify",
        suggested_optimal_final_action="abstain",
    )


# ── Dispatcher ────────────────────────────────────────────────────────────────

def apply_policy_uncertainty_operator(
    world: PolicyWorld,
    view: RenderedPolicyView,
    operator: PolicyOperatorName,
) -> UncertainPolicyView:
    if operator == "none":
        return no_uncertainty(world, view)
    if operator == "hide_threshold":
        return hide_threshold(world, view)
    if operator == "hide_exception":
        return hide_exception(world, view)
    if operator == "make_rule_ambiguous":
        return make_rule_ambiguous(world, view)
    if operator == "inject_conflict":
        return inject_conflict(world, view)
    if operator == "replace_exact_with_approximate":
        return replace_exact_with_approximate(world, view)
    if operator == "inject_policy_caveat":
        return inject_policy_caveat(world, view)
    if operator == "inject_incomplete_record":
        return inject_incomplete_record(world, view)
    if operator == "inject_unverifiable_requirement":
        return inject_unverifiable_requirement(world, view)
    if operator == "direct_answerable_hard":
        return direct_answerable_hard(world, view)
    if operator == "answerable_weak_verify":
        return answerable_weak_verify(world, view)
    if operator == "hint_resolves_missing_field":
        return hint_resolves_missing_field(world, view)
    if operator == "hint_resolves_exception":
        return hint_resolves_exception(world, view)
    if operator == "irrecoverable_missing_record":
        return irrecoverable_missing_record(world, view)
    if operator == "verify_residual_uncertainty":
        return verify_residual_uncertainty(world, view)
    raise ValueError(f"Unknown policy uncertainty operator: {operator}")


def apply_all_policy_uncertainty_operators(
    world: PolicyWorld,
    view: RenderedPolicyView,
) -> list[UncertainPolicyView]:
    return [
        no_uncertainty(world, view),
        hide_threshold(world, view),
        hide_exception(world, view),
        make_rule_ambiguous(world, view),
        inject_conflict(world, view),
        replace_exact_with_approximate(world, view),
        inject_policy_caveat(world, view),
        inject_incomplete_record(world, view),
        inject_unverifiable_requirement(world, view),
        direct_answerable_hard(world, view),
        answerable_weak_verify(world, view),
        hint_resolves_missing_field(world, view),
        hint_resolves_exception(world, view),
        irrecoverable_missing_record(world, view),
        verify_residual_uncertainty(world, view),
    ]
