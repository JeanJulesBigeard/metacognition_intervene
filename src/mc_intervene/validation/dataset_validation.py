from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable
import pandas as pd


REQUIRED_ACTIONS = {"answer", "ask_hint", "verify", "abstain"}
REQUIRED_FINAL_ACTIONS = {"answer", "abstain"}
REQUIRED_HINT_EFFECTS = {"resolve", "partial", "none"}
REQUIRED_VERIFY_EFFECTS = {
    "confirm",
    "weak_confirm",
    "warn",
    "ambiguous_support",
    "insufficient",
    "residual_uncertainty",
}
EXPECTED_POLICY_OPERATORS = {
    "none",
    "hide_threshold",
    "hide_exception",
    "make_rule_ambiguous",
    "inject_conflict",
    "replace_exact_with_approximate",
}

# Release-gate distribution bounds for optimal_first_action.
MIN_FIRST_ACTION_PCT: dict[str, float] = {
    "answer": 0.15,
    "ask_hint": 0.12,
    "verify": 0.30,
    "abstain": 0.12,
}
MAX_FIRST_ACTION_PCT: dict[str, float] = {
    "answer": 0.30,
    "ask_hint": 0.25,
    "verify": 0.50,
    "abstain": 0.30,
}

# Deterministic mapping: operator → (expected_first, expected_final).
# Operators with world-dependent optimal policy (e.g. replace_exact_with_approximate)
# are intentionally omitted.
EXPECTED_OPERATOR_POLICY: dict[str, tuple[str, str]] = {
    "none":                          ("answer",   "answer"),
    "direct_answerable_hard":        ("answer",   "answer"),
    "answerable_weak_verify":        ("answer",   "answer"),
    "hide_threshold":                ("ask_hint", "answer"),
    "hint_resolves_missing_field":   ("ask_hint", "answer"),
    "hint_resolves_exception":       ("ask_hint", "answer"),
    "hide_exception":                ("verify",   "answer"),
    "inject_conflict":               ("verify",   "answer"),
    "inject_policy_caveat":          ("verify",   "answer"),
    "inject_incomplete_record":      ("verify",   "abstain"),
    "verify_residual_uncertainty":   ("verify",   "abstain"),
    "make_rule_ambiguous":           ("abstain",  "abstain"),
    "inject_unverifiable_requirement": ("abstain","abstain"),
    "irrecoverable_missing_record":  ("abstain",  "abstain"),
}


@dataclass
class ValidationReport:
    n_rows: int
    n_bundles: int
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def raise_if_failed(self) -> None:
        if not self.passed:
            msg = "\n".join(["Dataset validation failed:"] + self.errors)
            raise ValueError(msg)


def _require_columns(df: pd.DataFrame, required: Iterable[str]) -> list[str]:
    missing = [c for c in required if c not in df.columns]
    return missing


def _is_missing(value) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


# ── Schema validation ─────────────────────────────────────────────────────────

def validate_required_columns(df: pd.DataFrame) -> list[str]:
    required = [
        "item_id",
        "world_id",
        "paired_item_group",
        "domain",
        "subtype",
        "variant",
        "prompt_text",
        "ground_truth",
        "uncertainty_source",
        "uncertainty_operator",
        "recoverability_type",
        "hint_effect",
        "verify_effect",
        "hint_payload",
        "verification_payload",
        "intervention_value_hint",
        "intervention_value_verify",
        "optimal_first_action",
        "optimal_final_action",
        "difficulty_band",
        "generator_family",
    ]
    missing = _require_columns(df, required)
    if missing:
        return [f"Missing required columns: {missing}"]
    return []


# ── Bundle-level validation ───────────────────────────────────────────────────

def validate_each_bundle_has_at_least_4_variants(df: pd.DataFrame) -> list[str]:
    errors = []
    bundle_sizes = df.groupby("paired_item_group")["variant"].nunique()
    bad = bundle_sizes[bundle_sizes < 4]
    for bundle_id, n_variants in bad.items():
        errors.append(
            f"Bundle {bundle_id!r} has only {n_variants} unique variants; expected at least 4."
        )
    return errors


def validate_optimal_first_action_varies_inside_bundle(df: pd.DataFrame) -> list[str]:
    errors = []
    action_counts = df.groupby("paired_item_group")["optimal_first_action"].nunique()
    bad = action_counts[action_counts < 2]
    for bundle_id, n_actions in bad.items():
        errors.append(
            f"Bundle {bundle_id!r} has only {n_actions} unique optimal_first_action; "
            f"expected at least 2."
        )
    return errors


def validate_rich_action_diversity(df: pd.DataFrame, min_actions: int = 3) -> list[str]:
    errors = []
    action_counts = df.groupby("paired_item_group")["optimal_first_action"].nunique()
    bad = action_counts[action_counts < min_actions]
    for bundle_id, n_actions in bad.items():
        errors.append(
            f"Bundle {bundle_id!r} has only {n_actions} unique optimal_first_action; "
            f"expected at least {min_actions} for rich counterfactual coverage."
        )
    return errors


def validate_bundle_operator_coverage(
    df: pd.DataFrame,
    required_operators: set[str] | None = None,
    strict: bool = False,
) -> list[str]:
    errors = []
    if required_operators is None:
        required_operators = EXPECTED_POLICY_OPERATORS

    for bundle_id, g in df.groupby("paired_item_group"):
        present = set(g["uncertainty_operator"].unique())
        if strict:
            missing = required_operators - present
            if missing:
                errors.append(
                    f"Bundle {bundle_id!r} is missing operators {sorted(missing)}. "
                    f"Present: {sorted(present)}"
                )
        else:
            if len(present) < 4:
                errors.append(
                    f"Bundle {bundle_id!r} has only {len(present)} uncertainty operators; "
                    f"expected at least 4. Present: {sorted(present)}"
                )
    return errors


# ── Dataset-level coverage validation ────────────────────────────────────────

def validate_verify_effect_is_covered(df: pd.DataFrame) -> list[str]:
    present = set(df["verify_effect"].dropna().unique())
    missing = REQUIRED_VERIFY_EFFECTS - present
    if missing:
        return [
            f"Dataset is missing verify_effect values: {sorted(missing)}. "
            f"Present values: {sorted(present)}"
        ]
    return []


def validate_hint_effect_is_covered(df: pd.DataFrame) -> list[str]:
    present = set(df["hint_effect"].dropna().unique())
    missing = REQUIRED_HINT_EFFECTS - present
    if missing:
        return [
            f"Dataset is missing hint_effect values: {sorted(missing)}. "
            f"Present values: {sorted(present)}"
        ]
    return []


def warn_low_verify_effect_coverage(
    df: pd.DataFrame,
    min_count: int = 10,
) -> list[str]:
    warnings = []
    counts = df["verify_effect"].value_counts()
    for effect in REQUIRED_VERIFY_EFFECTS:
        count = int(counts.get(effect, 0))
        if count < min_count:
            warnings.append(
                f"verify_effect={effect!r} has only {count} examples; "
                f"recommended at least {min_count}."
            )
    return warnings


def warn_low_hint_effect_coverage(
    df: pd.DataFrame,
    min_count: int = 10,
) -> list[str]:
    warnings = []
    counts = df["hint_effect"].value_counts()
    for effect in REQUIRED_HINT_EFFECTS:
        count = int(counts.get(effect, 0))
        if count < min_count:
            warnings.append(
                f"hint_effect={effect!r} has only {count} examples; "
                f"recommended at least {min_count}."
            )
    return warnings


# ── Ground truth validation ───────────────────────────────────────────────────

def validate_ground_truth_is_deterministic(df: pd.DataFrame) -> list[str]:
    errors = []
    allowed = {"yes", "no", "unknown", "ambiguous"}

    missing_gt = df[df["ground_truth"].apply(_is_missing)]
    if len(missing_gt) > 0:
        errors.append(
            f"{len(missing_gt)} rows have missing ground_truth. "
            f"Example item_ids: {missing_gt['item_id'].head(5).tolist()}"
        )

    invalid = df[~df["ground_truth"].isin(allowed)]
    if len(invalid) > 0:
        errors.append(
            f"{len(invalid)} rows have invalid ground_truth values. "
            f"Allowed: {sorted(allowed)}. "
            f"Examples: {invalid[['item_id', 'ground_truth']].head(5).to_dict('records')}"
        )

    gt_by_world = df.groupby("world_id")["ground_truth"].nunique()
    bad_worlds = gt_by_world[gt_by_world > 1]
    for world_id, n_truths in bad_worlds.items():
        vals = sorted(df.loc[df["world_id"] == world_id, "ground_truth"].unique().tolist())
        errors.append(
            f"world_id={world_id!r} has {n_truths} different ground_truth values: {vals}. "
            f"Ground truth must be deterministic per hidden world."
        )

    return errors


# ── Payload validation ────────────────────────────────────────────────────────

def validate_no_active_payload_is_missing(df: pd.DataFrame) -> list[str]:
    errors = []

    missing_hint = df[df["hint_payload"].apply(_is_missing)]
    if len(missing_hint) > 0:
        errors.append(
            f"{len(missing_hint)} rows have missing hint_payload. "
            f"Examples: {missing_hint['item_id'].head(5).tolist()}"
        )

    missing_verify = df[df["verification_payload"].apply(_is_missing)]
    if len(missing_verify) > 0:
        errors.append(
            f"{len(missing_verify)} rows have missing verification_payload. "
            f"Examples: {missing_verify['item_id'].head(5).tolist()}"
        )

    ask_hint_rows = df[df["optimal_first_action"] == "ask_hint"]
    bad_ask_hint = ask_hint_rows[ask_hint_rows["hint_payload"].apply(_is_missing)]
    if len(bad_ask_hint) > 0:
        errors.append(
            f"{len(bad_ask_hint)} ask_hint-optimal rows have missing hint_payload. "
            f"Examples: {bad_ask_hint['item_id'].head(5).tolist()}"
        )

    verify_rows = df[df["optimal_first_action"] == "verify"]
    bad_verify = verify_rows[verify_rows["verification_payload"].apply(_is_missing)]
    if len(bad_verify) > 0:
        errors.append(
            f"{len(bad_verify)} verify-optimal rows have missing verification_payload. "
            f"Examples: {bad_verify['item_id'].head(5).tolist()}"
        )

    active_hint_rows = df[df["hint_effect"] != "none"]
    bad_active_hint = active_hint_rows[active_hint_rows["hint_payload"].apply(_is_missing)]
    if len(bad_active_hint) > 0:
        errors.append(
            f"{len(bad_active_hint)} rows with active hint_effect have missing hint_payload. "
            f"Examples: {bad_active_hint['item_id'].head(5).tolist()}"
        )

    return errors


# ── Action label validation ───────────────────────────────────────────────────

def validate_action_labels(df: pd.DataFrame) -> list[str]:
    errors = []

    first_actions = set(df["optimal_first_action"].dropna().unique())
    bad_first = first_actions - REQUIRED_ACTIONS
    if bad_first:
        errors.append(
            f"Invalid optimal_first_action values: {sorted(bad_first)}. "
            f"Allowed: {sorted(REQUIRED_ACTIONS)}"
        )

    final_actions = set(df["optimal_final_action"].dropna().unique())
    bad_final = final_actions - REQUIRED_FINAL_ACTIONS
    if bad_final:
        errors.append(
            f"Invalid optimal_final_action values: {sorted(bad_final)}. "
            f"Allowed: {sorted(REQUIRED_FINAL_ACTIONS)}"
        )

    return errors


# ── Intervention value validation ─────────────────────────────────────────────

def validate_first_action_covers_all_four(df: pd.DataFrame) -> list[str]:
    present = set(df["optimal_first_action"].dropna().unique())
    missing = REQUIRED_ACTIONS - present
    if missing:
        return [
            f"Dataset is missing optimal_first_action values: {sorted(missing)}. "
            f"All four actions (answer, ask_hint, verify, abstain) must appear as first actions."
        ]
    return []


def validate_epistemic_answerability_consistent(df: pd.DataFrame) -> list[str]:
    if "epistemic_answerability" not in df.columns:
        return []

    allowed = {"answerable", "not_answerable"}
    bad_values = set(df["epistemic_answerability"].dropna().unique()) - allowed
    errors = []
    if bad_values:
        errors.append(
            f"Invalid epistemic_answerability values: {sorted(bad_values)}. "
            f"Allowed: {sorted(allowed)}"
        )

    # answerable iff optimal_final_action == "answer"
    inconsistent = df[
        ((df["epistemic_answerability"] == "answerable") & (df["optimal_final_action"] != "answer"))
        | ((df["epistemic_answerability"] == "not_answerable") & (df["optimal_final_action"] == "answer"))
    ]
    if len(inconsistent) > 0:
        errors.append(
            f"{len(inconsistent)} rows have epistemic_answerability inconsistent with "
            f"optimal_final_action. Examples: "
            f"{inconsistent[['item_id', 'epistemic_answerability', 'optimal_final_action']].head(5).to_dict('records')}"
        )

    return errors


def validate_intervention_values(df: pd.DataFrame) -> list[str]:
    errors = []
    allowed = {"high", "medium", "low", "negative"}

    for col in ["intervention_value_hint", "intervention_value_verify"]:
        values = set(df[col].dropna().unique())
        bad = values - allowed
        if bad:
            errors.append(
                f"Invalid {col} values: {sorted(bad)}. Allowed: {sorted(allowed)}"
            )

    bad_hint_optimal = df[
        (df["optimal_first_action"] == "ask_hint")
        & (~df["intervention_value_hint"].isin(["high", "medium"]))
    ]
    if len(bad_hint_optimal) > 0:
        errors.append(
            f"{len(bad_hint_optimal)} ask_hint-optimal rows do not have medium/high hint value. "
            f"Examples: {bad_hint_optimal[['item_id', 'intervention_value_hint']].head(5).to_dict('records')}"
        )

    bad_verify_optimal = df[
        (df["optimal_first_action"] == "verify")
        & (~df["intervention_value_verify"].isin(["high", "medium"]))
    ]
    if len(bad_verify_optimal) > 0:
        errors.append(
            f"{len(bad_verify_optimal)} verify-optimal rows do not have medium/high verify value. "
            f"Examples: {bad_verify_optimal[['item_id', 'intervention_value_verify']].head(5).to_dict('records')}"
        )

    return errors


# ── Distribution validation ───────────────────────────────────────────────────

def validate_optimal_first_action_distribution(
    df: pd.DataFrame,
    min_pct: dict[str, float] | None = None,
    max_pct: dict[str, float] | None = None,
) -> list[str]:
    if min_pct is None:
        min_pct = MIN_FIRST_ACTION_PCT
    if max_pct is None:
        max_pct = MAX_FIRST_ACTION_PCT

    errors = []
    total = len(df)
    if total == 0:
        return errors

    counts = df["optimal_first_action"].value_counts()
    for action in set(list(min_pct.keys()) + list(max_pct.keys())):
        n = int(counts.get(action, 0))
        pct = n / total
        lo = min_pct.get(action, 0.0)
        hi = max_pct.get(action, 1.0)
        if pct < lo:
            errors.append(
                f"optimal_first_action={action!r}: {n}/{total} = {pct:.1%} "
                f"is below minimum {lo:.1%}."
            )
        elif pct > hi:
            errors.append(
                f"optimal_first_action={action!r}: {n}/{total} = {pct:.1%} "
                f"exceeds maximum {hi:.1%}."
            )
    return errors


# ── Operator-policy consistency validation ────────────────────────────────────

def validate_operator_policy_consistency(df: pd.DataFrame) -> list[str]:
    errors = []
    for op, (expected_first, expected_final) in EXPECTED_OPERATOR_POLICY.items():
        rows = df[df["uncertainty_operator"] == op]
        if rows.empty:
            continue
        bad_first = rows[rows["optimal_first_action"] != expected_first]
        if len(bad_first) > 0:
            errors.append(
                f"operator={op!r}: {len(bad_first)} rows have "
                f"optimal_first_action != {expected_first!r}. "
                f"Examples: {bad_first[['item_id', 'optimal_first_action']].head(3).to_dict('records')}"
            )
        bad_final = rows[rows["optimal_final_action"] != expected_final]
        if len(bad_final) > 0:
            errors.append(
                f"operator={op!r}: {len(bad_final)} rows have "
                f"optimal_final_action != {expected_final!r}. "
                f"Examples: {bad_final[['item_id', 'optimal_final_action']].head(3).to_dict('records')}"
            )
    return errors


# ── Main ──────────────────────────────────────────────────────────────────────

def validate_dataset(
    df: pd.DataFrame,
    *,
    strict_bundle_operators: bool = False,
    min_effect_count: int = 10,
    require_rich_action_diversity: bool = False,
    check_distribution: bool = False,
) -> ValidationReport:
    errors: list[str] = []
    warnings: list[str] = []

    if df.empty:
        return ValidationReport(
            n_rows=0,
            n_bundles=0,
            passed=False,
            errors=["Dataset is empty."],
            warnings=[],
        )

    errors.extend(validate_required_columns(df))

    # Stop early to avoid cascading KeyErrors on missing columns.
    if errors:
        return ValidationReport(
            n_rows=len(df),
            n_bundles=0,
            passed=False,
            errors=errors,
            warnings=warnings,
        )

    errors.extend(validate_each_bundle_has_at_least_4_variants(df))
    errors.extend(validate_optimal_first_action_varies_inside_bundle(df))

    if require_rich_action_diversity:
        errors.extend(validate_rich_action_diversity(df, min_actions=3))

    errors.extend(validate_verify_effect_is_covered(df))
    errors.extend(validate_hint_effect_is_covered(df))
    errors.extend(validate_ground_truth_is_deterministic(df))
    errors.extend(validate_no_active_payload_is_missing(df))
    errors.extend(validate_action_labels(df))
    errors.extend(validate_first_action_covers_all_four(df))
    errors.extend(validate_epistemic_answerability_consistent(df))
    errors.extend(validate_bundle_operator_coverage(df, strict=strict_bundle_operators))
    errors.extend(validate_intervention_values(df))
    errors.extend(validate_operator_policy_consistency(df))

    if check_distribution:
        errors.extend(validate_optimal_first_action_distribution(df))

    warnings.extend(warn_low_verify_effect_coverage(df, min_count=min_effect_count))
    warnings.extend(warn_low_hint_effect_coverage(df, min_count=min_effect_count))

    return ValidationReport(
        n_rows=len(df),
        n_bundles=df["paired_item_group"].nunique(),
        passed=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
