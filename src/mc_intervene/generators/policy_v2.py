from __future__ import annotations

from typing import Sequence

import pandas as pd

from mc_intervene.worlds.policy_world import (
    PolicyWorld,
    generate_policy_worlds,
    validate_policy_world,
)
from mc_intervene.renderers.policy_renderers import (
    render_policy_world,
    PolicyViewType,
)
from mc_intervene.operators.policy_uncertainty import (
    apply_policy_uncertainty_operator,
    PolicyOperatorName,
)
from mc_intervene.operators.validation import validate_uncertain_policy_view
from mc_intervene.interventions.policy_interventions import (
    build_policy_intervention_spec,
)
from mc_intervene.interventions.validation import validate_policy_intervention_spec
from mc_intervene.validation import validate_dataset


# ── Operator groups by expected optimal_first_action ─────────────────────────

ANSWER_OPERATORS: tuple[PolicyOperatorName, ...] = (
    "none",
    "direct_answerable_hard",
    "answerable_weak_verify",
)

ASK_HINT_OPERATORS: tuple[PolicyOperatorName, ...] = (
    "hide_threshold",
    "hint_resolves_missing_field",
    "hint_resolves_exception",
)

VERIFY_OPERATORS: tuple[PolicyOperatorName, ...] = (
    "hide_exception",
    "inject_conflict",
    "inject_policy_caveat",
    "inject_incomplete_record",
    "verify_residual_uncertainty",
)

ABSTAIN_OPERATORS: tuple[PolicyOperatorName, ...] = (
    "make_rule_ambiguous",
    "inject_unverifiable_requirement",
    "irrecoverable_missing_record",
)

# Recipe: how many to pick from each group per bundle.
# 2 + 2 + 3 + 2 = 9 operators → 9 rows per bundle.
# VERIFY has 5 ops (pick 3); ABSTAIN has 3 ops (pick 2).
BUNDLE_RECIPE: dict[str, int] = {
    "answer": 2,
    "ask_hint": 2,
    "verify": 3,
    "abstain": 2,
}

_OPERATOR_GROUPS = {
    "answer": ANSWER_OPERATORS,
    "ask_hint": ASK_HINT_OPERATORS,
    "verify": VERIFY_OPERATORS,
    "abstain": ABSTAIN_OPERATORS,
}

DEFAULT_POLICY_V2_VIEW_TYPES: tuple[PolicyViewType, ...] = (
    "short_narrative",
    "policy_excerpt",
    "evidence_bundle",
    "table_record",
)


def _rotate_pick(ops: tuple, n: int, bundle_idx: int) -> list[PolicyOperatorName]:
    """
    Pick n items from ops using deterministic round-robin rotation.

    Over many bundles, each operator in ops appears in approximately
    n/len(ops) fraction of bundles, giving uniform coverage.
    """
    total = len(ops)
    start = (bundle_idx * n) % total
    return [ops[(start + i) % total] for i in range(n)]


def _select_bundle_operators(bundle_idx: int) -> list[PolicyOperatorName]:
    selected: list[PolicyOperatorName] = []
    for group_name, n_picks in BUNDLE_RECIPE.items():
        group_ops = _OPERATOR_GROUPS[group_name]
        selected.extend(_rotate_pick(group_ops, n_picks, bundle_idx))
    return selected


def _difficulty_band(operator: str, view_type: str) -> str:
    if operator in {"none", "direct_answerable_hard"}:
        return "easy"
    if operator in {
        "hide_threshold", "hide_exception",
        "answerable_weak_verify", "hint_resolves_missing_field",
        "hint_resolves_exception",
    }:
        return "medium"
    if operator in {
        "make_rule_ambiguous",
        "inject_conflict",
        "replace_exact_with_approximate",
        "inject_policy_caveat",
        "inject_incomplete_record",
        "inject_unverifiable_requirement",
        "irrecoverable_missing_record",
        "verify_residual_uncertainty",
    }:
        return "hard"
    return "medium"


def _serialize_acceptable_actions(actions: list[str]) -> str:
    return ",".join(actions) if actions else ""


def build_policy_v2_row(
    *,
    world: PolicyWorld,
    bundle_id: str,
    variant_idx: int,
    view_type: PolicyViewType,
    operator: PolicyOperatorName,
) -> dict:
    """
    Build one task-ready row from:

    PolicyWorld
      -> RenderedPolicyView
      -> UncertainPolicyView
      -> PolicyInterventionSpec
      -> row dict
    """
    validate_policy_world(world)

    rendered_view = render_policy_world(world, view_type)
    uncertain_view = apply_policy_uncertainty_operator(
        world=world,
        view=rendered_view,
        operator=operator,
    )
    validate_uncertain_policy_view(uncertain_view)

    spec = build_policy_intervention_spec(world, uncertain_view)
    validate_policy_intervention_spec(uncertain_view, spec)

    item_id = f"{world.world_id}_{view_type}_{operator}_{variant_idx}"

    return {
        "item_id": item_id,
        "world_id": world.world_id,
        "paired_item_group": bundle_id,

        "task_family": "mc_intervene_v2",
        "domain": "policy_eligibility",
        "subtype": "policy_case",
        "variant": operator,
        "view_type": view_type,

        "prompt_text": uncertain_view.prompt_text,
        "ground_truth": world.ground_truth,
        "latent_ground_truth": world.ground_truth,
        "epistemic_answerability": (
            "answerable" if spec.optimal_final_action == "answer" else "not_answerable"
        ),

        "uncertainty_source": uncertain_view.uncertainty_source,
        "uncertainty_operator": uncertain_view.uncertainty_operator,
        "recoverability_type": uncertain_view.recoverability_type,

        "hint_effect": spec.hint_effect,
        "verify_effect": spec.verify_effect,
        "hint_payload": spec.hint_payload,
        "verification_payload": spec.verification_payload,

        "intervention_value_hint": spec.intervention_value_hint,
        "intervention_value_verify": spec.intervention_value_verify,

        "optimal_first_action": spec.optimal_first_action,
        "optimal_final_action": spec.optimal_final_action,
        "acceptable_first_actions": _serialize_acceptable_actions(
            spec.acceptable_first_actions
        ),

        "difficulty_band": _difficulty_band(operator, view_type),
        "generator_family": "policy_world_v2",

        "policy_notes": spec.policy_notes,
        "operator_notes": uncertain_view.operator_notes,
        "hidden_fields": "|".join(uncertain_view.hidden_fields),
        "degraded_fields": "|".join(uncertain_view.degraded_fields),
    }


def generate_policy_bundle(
    world: PolicyWorld,
    *,
    bundle_idx: int,
    view_type: PolicyViewType,
    operators: Sequence[PolicyOperatorName] | None = None,
) -> list[dict]:
    """
    Generate all counterfactual variants for one hidden world.

    If operators is None, uses the balanced recipe for bundle_idx.
    One bundle uses one view_type so the counterfactual comparison is clean.
    """
    bundle_id = f"policy_bundle_{bundle_idx}"

    if operators is None:
        operators = _select_bundle_operators(bundle_idx)

    rows = []
    for variant_idx, operator in enumerate(operators):
        row = build_policy_v2_row(
            world=world,
            bundle_id=bundle_id,
            variant_idx=variant_idx,
            view_type=view_type,
            operator=operator,
        )
        rows.append(row)

    return rows


def build_policy_v2_df(
    *,
    n_bundles: int = 100,
    seed: int = 67,
    view_types: Sequence[PolicyViewType] = DEFAULT_POLICY_V2_VIEW_TYPES,
    operators: Sequence[PolicyOperatorName] | None = None,
    validate: bool = True,
    strict_validation: bool = False,
) -> pd.DataFrame:
    """
    Build a v2 policy/eligibility metacognitive intervention dataset.

    Uses the balanced operator recipe by default (2 answer + 2 ask_hint +
    3 verify + 2 abstain = 9 operators per bundle, 900 rows for 100 bundles).
    Pass operators= to override with a fixed list for all bundles.
    """
    worlds = generate_policy_worlds(n_worlds=n_bundles, seed=seed)

    rows = []
    for bundle_idx, world in enumerate(worlds):
        view_type = view_types[bundle_idx % len(view_types)]
        bundle_rows = generate_policy_bundle(
            world,
            bundle_idx=bundle_idx,
            view_type=view_type,
            operators=operators,
        )
        rows.extend(bundle_rows)

    df = pd.DataFrame(rows)

    if validate:
        report = validate_dataset(
            df,
            strict_bundle_operators=strict_validation,
            require_rich_action_diversity=True,
            min_effect_count=max(1, n_bundles // 20),
        )

        for warning in report.warnings:
            print("[WARNING]", warning)

        report.raise_if_failed()

    return df
