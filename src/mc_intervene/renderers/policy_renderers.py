from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from mc_intervene.worlds.policy_world import PolicyWorld


PolicyViewType = Literal[
    "short_narrative",
    "policy_excerpt",
    "evidence_bundle",
    "table_record",
]


@dataclass(frozen=True)
class RenderedPolicyView:
    """
    Public-facing representation of a hidden PolicyWorld.

    This is an intermediate object. It is not yet a benchmark row.
    Later uncertainty operators will transform this view into variants:
    direct_answerable, missing_threshold, verify_critical, irrecoverable, etc.
    """

    world_id: str
    view_type: PolicyViewType
    prompt_text: str

    # Structured fields for later corruption/removal.
    visible_facts: dict[str, str] = field(default_factory=dict)
    visible_policy_parts: dict[str, str] = field(default_factory=dict)
    evidence_fragments: list[str] = field(default_factory=list)

    # Metadata useful for validation and diagnostics.
    contains_full_policy: bool = False
    contains_threshold: bool = False
    contains_exception: bool = False
    contains_form_requirement: bool = False
    contains_priority_status: bool = False
    contains_days_early: bool = False


def render_short_narrative(world: PolicyWorld) -> RenderedPolicyView:
    prompt = (
        f"{world.entity} completed the {world.event_name} "
        f"{world.days_early} days before the deadline. "
    )
    if world.has_priority_status:
        prompt += f"{world.entity} has priority status. "
    else:
        prompt += f"{world.entity} does not have priority status. "
    if world.submitted_required_form:
        prompt += f"{world.entity} submitted the required form. "
    else:
        prompt += f"{world.entity} did not submit the required form. "
    prompt += (
        f"The policy says that regular entities need to complete the "
        f"{world.event_name} at least {world.base_threshold_days} days early "
        f"to receive the {world.benefit_name}. "
        f"Priority entities only need {world.priority_threshold_days} days early. "
    )
    if world.requires_form:
        prompt += "A required form must also be submitted. "
    else:
        prompt += "No additional form is required. "
    prompt += f"Did {world.entity} qualify for the {world.benefit_name}?"

    return RenderedPolicyView(
        world_id=world.world_id,
        view_type="short_narrative",
        prompt_text=prompt,
        visible_facts={
            "days_early": str(world.days_early),
            "has_priority_status": str(world.has_priority_status),
            "submitted_required_form": str(world.submitted_required_form),
        },
        visible_policy_parts={
            "base_threshold_days": str(world.base_threshold_days),
            "priority_threshold_days": str(world.priority_threshold_days),
            "requires_form": str(world.requires_form),
        },
        contains_full_policy=True,
        contains_threshold=True,
        contains_exception=True,
        contains_form_requirement=True,
        contains_priority_status=True,
        contains_days_early=True,
    )


def render_policy_excerpt(world: PolicyWorld) -> RenderedPolicyView:
    facts = (
        f"Case facts:\n"
        f"- Entity: {world.entity}\n"
        f"- Event: {world.event_name}\n"
        f"- Completed: {world.days_early} days before the deadline\n"
        f"- Priority status: {'yes' if world.has_priority_status else 'no'}\n"
        f"- Required form submitted: {'yes' if world.submitted_required_form else 'no'}"
    )
    policy = (
        f"Policy excerpt:\n"
        f"- Regular entities qualify for the {world.benefit_name} if they complete "
        f"the {world.event_name} at least {world.base_threshold_days} days before the deadline.\n"
        f"- Priority entities qualify if they complete it at least "
        f"{world.priority_threshold_days} days before the deadline.\n"
        f"- Form requirement: "
        f"{'a required form must be submitted' if world.requires_form else 'no additional form is required'}."
    )
    prompt = (
        f"{facts}\n\n"
        f"{policy}\n\n"
        f"Question: Did {world.entity} qualify for the {world.benefit_name}?"
    )

    return RenderedPolicyView(
        world_id=world.world_id,
        view_type="policy_excerpt",
        prompt_text=prompt,
        visible_facts={
            "entity": world.entity,
            "event_name": world.event_name,
            "days_early": str(world.days_early),
            "has_priority_status": "yes" if world.has_priority_status else "no",
            "submitted_required_form": "yes" if world.submitted_required_form else "no",
        },
        visible_policy_parts={
            "base_threshold_days": str(world.base_threshold_days),
            "priority_threshold_days": str(world.priority_threshold_days),
            "requires_form": "yes" if world.requires_form else "no",
        },
        evidence_fragments=[facts, policy],
        contains_full_policy=True,
        contains_threshold=True,
        contains_exception=True,
        contains_form_requirement=True,
        contains_priority_status=True,
        contains_days_early=True,
    )


def render_evidence_bundle(world: PolicyWorld) -> RenderedPolicyView:
    fragment_case_summary = (
        f"Evidence A — Case summary:\n"
        f"{world.entity} completed the {world.event_name} "
        f"{world.days_early} days before the deadline."
    )
    fragment_status = (
        f"Evidence B — Status record:\n"
        f"Priority status: {'active' if world.has_priority_status else 'not active'}."
    )
    fragment_form = (
        f"Evidence C — Form record:\n"
        f"Required form submitted: {'yes' if world.submitted_required_form else 'no'}."
    )
    fragment_policy = (
        f"Evidence D — Policy rule:\n"
        f"Regular entities require at least {world.base_threshold_days} days early. "
        f"Priority entities require at least {world.priority_threshold_days} days early."
    )
    fragment_form_policy = (
        f"Evidence E — Administrative requirement:\n"
        f"{'A required form must be submitted.' if world.requires_form else 'No additional form is required.'}"
    )

    fragments = [
        fragment_case_summary,
        fragment_status,
        fragment_form,
        fragment_policy,
        fragment_form_policy,
    ]
    prompt = (
        "Review the evidence fragments below and answer the question.\n\n"
        + "\n\n".join(fragments)
        + f"\n\nQuestion: Did {world.entity} qualify for the {world.benefit_name}?"
    )

    return RenderedPolicyView(
        world_id=world.world_id,
        view_type="evidence_bundle",
        prompt_text=prompt,
        visible_facts={
            "days_early": str(world.days_early),
            "has_priority_status": "active" if world.has_priority_status else "not_active",
            "submitted_required_form": "yes" if world.submitted_required_form else "no",
        },
        visible_policy_parts={
            "base_threshold_days": str(world.base_threshold_days),
            "priority_threshold_days": str(world.priority_threshold_days),
            "requires_form": "yes" if world.requires_form else "no",
        },
        evidence_fragments=fragments,
        contains_full_policy=True,
        contains_threshold=True,
        contains_exception=True,
        contains_form_requirement=True,
        contains_priority_status=True,
        contains_days_early=True,
    )


def render_table_record(world: PolicyWorld) -> RenderedPolicyView:
    table = (
        f"| Field | Value |\n"
        f"|---|---|\n"
        f"| Entity | {world.entity} |\n"
        f"| Benefit | {world.benefit_name} |\n"
        f"| Event | {world.event_name} |\n"
        f"| Days before deadline | {world.days_early} |\n"
        f"| Priority status | {'yes' if world.has_priority_status else 'no'} |\n"
        f"| Required form submitted | {'yes' if world.submitted_required_form else 'no'} |\n"
        f"| Regular threshold | {world.base_threshold_days} days |\n"
        f"| Priority threshold | {world.priority_threshold_days} days |\n"
        f"| Form required by policy | {'yes' if world.requires_form else 'no'} |"
    )
    prompt = (
        f"Use the table below to determine eligibility.\n\n"
        f"{table}\n\n"
        f"Question: Did {world.entity} qualify for the {world.benefit_name}?"
    )

    return RenderedPolicyView(
        world_id=world.world_id,
        view_type="table_record",
        prompt_text=prompt,
        visible_facts={
            "days_early": str(world.days_early),
            "has_priority_status": "yes" if world.has_priority_status else "no",
            "submitted_required_form": "yes" if world.submitted_required_form else "no",
        },
        visible_policy_parts={
            "base_threshold_days": str(world.base_threshold_days),
            "priority_threshold_days": str(world.priority_threshold_days),
            "requires_form": "yes" if world.requires_form else "no",
        },
        evidence_fragments=[table],
        contains_full_policy=True,
        contains_threshold=True,
        contains_exception=True,
        contains_form_requirement=True,
        contains_priority_status=True,
        contains_days_early=True,
    )


def render_policy_world(
    world: PolicyWorld,
    view_type: PolicyViewType,
) -> RenderedPolicyView:
    if view_type == "short_narrative":
        return render_short_narrative(world)
    if view_type == "policy_excerpt":
        return render_policy_excerpt(world)
    if view_type == "evidence_bundle":
        return render_evidence_bundle(world)
    if view_type == "table_record":
        return render_table_record(world)
    raise ValueError(f"Unknown policy view_type: {view_type}")


def render_all_policy_views(world: PolicyWorld) -> list[RenderedPolicyView]:
    return [
        render_short_narrative(world),
        render_policy_excerpt(world),
        render_evidence_bundle(world),
        render_table_record(world),
    ]
