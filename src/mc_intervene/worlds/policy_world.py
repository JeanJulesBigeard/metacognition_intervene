from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Literal


GroundTruth = Literal["yes", "no"]


@dataclass(frozen=True)
class PolicyWorld:
    """
    Hidden structured state for one policy / eligibility scenario.

    This object is NOT shown directly to the model.
    It is the source of truth from which multiple counterfactual
    benchmark variants are generated.
    """

    world_id: str
    entity: str
    program_name: str

    # Observable factual state
    days_early: int
    submitted_required_form: bool
    has_priority_status: bool

    # Hidden policy state
    base_threshold_days: int
    priority_threshold_days: int
    requires_form: bool

    # Natural-language labels
    event_name: str
    benefit_name: str

    @property
    def effective_threshold_days(self) -> int:
        if self.has_priority_status:
            return self.priority_threshold_days
        return self.base_threshold_days

    @property
    def qualifies(self) -> bool:
        time_ok = self.days_early >= self.effective_threshold_days
        form_ok = True if not self.requires_form else self.submitted_required_form
        return time_ok and form_ok

    @property
    def ground_truth(self) -> GroundTruth:
        return "yes" if self.qualifies else "no"

    @property
    def public_fact_summary(self) -> str:
        timing = (
            f"{self.entity} completed {self.event_name} "
            f"{self.days_early} days before the deadline."
        )
        form = (
            f"{self.entity} submitted the required form."
            if self.submitted_required_form
            else f"{self.entity} did not submit the required form."
        )
        priority = (
            f"{self.entity} has priority status."
            if self.has_priority_status
            else f"{self.entity} does not have priority status."
        )
        return f"{timing} {form} {priority}"

    @property
    def full_policy_text(self) -> str:
        return (
            f"To receive the {self.benefit_name}, an entity must complete "
            f"{self.event_name} at least {self.base_threshold_days} days before "
            f"the deadline. Entities with priority status only need to complete it "
            f"{self.priority_threshold_days} days before the deadline. "
            f"{'A required form must also be submitted.' if self.requires_form else 'No additional form is required.'}"
        )

    def decision_explanation(self) -> str:
        return (
            f"Effective threshold: {self.effective_threshold_days} days early. "
            f"Observed: {self.days_early} days early. "
            f"Requires form: {self.requires_form}. "
            f"Submitted form: {self.submitted_required_form}. "
            f"Ground truth: {self.ground_truth}."
        )


ENTITIES = [
    "Project Helix",
    "Project Nova",
    "Project Orion",
    "Project Atlas",
    "Team Mercury",
    "Team Delta",
    "Application R-17",
    "Application K-42",
]

PROGRAMS = [
    ("early-completion bonus", "milestone review"),
    ("fast-track approval", "compliance package"),
    ("priority reimbursement", "expense filing"),
    ("deployment credit", "release checklist"),
    ("expedited certification", "safety review"),
]


def sample_policy_world(rng: random.Random, idx: int) -> PolicyWorld:
    """
    Sample one hidden policy world.

    Near-threshold cases are intentionally over-represented because those
    are the most useful for metacognitive intervention testing.
    """
    entity = rng.choice(ENTITIES)
    benefit_name, event_name = rng.choice(PROGRAMS)

    base_threshold_days = rng.choice([3, 5, 7, 10])
    priority_threshold_days = max(1, base_threshold_days - rng.choice([2, 3, 4]))

    days_early = rng.choice([
        base_threshold_days - 2,
        base_threshold_days - 1,
        base_threshold_days,
        base_threshold_days + 1,
        base_threshold_days + 2,   # extra above-threshold to widen timing-pass coverage
        priority_threshold_days - 1,
        priority_threshold_days,
        priority_threshold_days + 1,
    ])
    days_early = max(0, days_early)

    has_priority_status = rng.choice([True, False])
    requires_form = rng.choice([True, False])
    # Bias toward submitted so form-fail fallbacks don't gut the hint-operator rows.
    submitted_required_form = rng.choice([True, True, True, False])

    return PolicyWorld(
        world_id=f"policy_world_{idx}",
        entity=entity,
        program_name=benefit_name,
        days_early=days_early,
        submitted_required_form=submitted_required_form,
        has_priority_status=has_priority_status,
        base_threshold_days=base_threshold_days,
        priority_threshold_days=priority_threshold_days,
        requires_form=requires_form,
        event_name=event_name,
        benefit_name=benefit_name,
    )


def generate_policy_worlds(n_worlds: int, seed: int = 67) -> list[PolicyWorld]:
    rng = random.Random(seed)
    return [sample_policy_world(rng, idx=i) for i in range(n_worlds)]


def validate_policy_world(world: PolicyWorld) -> None:
    assert world.world_id
    assert world.entity
    assert world.program_name
    assert world.base_threshold_days >= world.priority_threshold_days
    assert world.priority_threshold_days >= 1
    assert world.days_early >= 0
    assert world.ground_truth in {"yes", "no"}

    expected = (
        world.days_early >= world.effective_threshold_days
        and (not world.requires_form or world.submitted_required_form)
    )
    assert world.qualifies == expected
