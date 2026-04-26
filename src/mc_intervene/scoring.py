from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from mc_intervene.schema import MetaAction


@dataclass
class EpisodeResult:
    item_id: str
    final_score: float
    outcome_score: float
    control_score: float
    calibration_score: float
    confidence_dynamics_score: float
    efficiency_score: float
    first_action: str
    final_action: str
    final_correct: bool
    final_safe: bool


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def normalize_text(text):
    if text is None:
        return ""
    return " ".join(str(text).strip().lower().split())


def is_answer_correct(pred, gold) -> bool:
    return normalize_text(pred) == normalize_text(gold)


def is_nonanswerable(row: dict) -> bool:
    return normalize_text(row["ground_truth"]) in {"unknown", "ambiguous"}


def validate_meta_action(action: MetaAction) -> None:
    if action.action == "answer" and not action.answer:
        raise ValueError("Action 'answer' requires a non-empty answer")
    if action.action in {"ask_hint", "verify", "abstain"} and action.answer is not None:
        raise ValueError(f"Action '{action.action}' must not include an answer")


def outcome_score_from_final_state(row, final_action, final_answer):
    gold = row["ground_truth"]

    if final_action == "abstain":
        if is_nonanswerable(row):
            return 1.0, True, True
        return 0.3, False, False

    if final_action == "answer":
        if is_nonanswerable(row):
            return 0.0, False, False
        correct = is_answer_correct(final_answer, gold)
        return (1.0 if correct else 0.0), correct, correct

    return 0.0, False, False


def score_first_action(row, first_action: MetaAction) -> float:
    optimal = row["optimal_first_action"]

    if first_action.action == optimal:
        return 1.0

    if optimal == "answer" and first_action.action in {"ask_hint", "verify"}:
        return 0.25
    if optimal == "abstain" and first_action.action in {"ask_hint", "verify"}:
        return 0.35
    if optimal in {"ask_hint", "verify"} and first_action.action == "answer":
        return 0.10
    if optimal == "answer" and first_action.action == "abstain":
        return 0.15
    if optimal in {"ask_hint", "verify"} and first_action.action == "abstain":
        return 0.40

    return 0.0


def score_transition(row, first_action: MetaAction, second_action: Optional[MetaAction]) -> float:
    if first_action.action in {"answer", "abstain"}:
        return 1.0 if second_action is None else 0.2

    if second_action is None:
        return 0.0

    if first_action.action == "ask_hint":
        effect = row["hint_effect"]

        if effect == "resolve":
            return 1.0 if second_action.action == "answer" else 0.35 if second_action.action == "abstain" else 0.0
        if effect == "partial":
            return 1.0 if second_action.action == "abstain" else 0.15 if second_action.action == "answer" else 0.0
        if effect == "none":
            return 1.0 if second_action.action == "abstain" else 0.05 if second_action.action == "answer" else 0.0

    if first_action.action == "verify":
        effect = row["verify_effect"]

        if effect == "confirm":
            return 1.0 if second_action.action == "answer" else 0.25 if second_action.action == "abstain" else 0.0
        if effect == "weak_confirm":
            return 0.75 if second_action.action == "answer" else 0.55 if second_action.action == "abstain" else 0.0
        if effect == "warn":
            return 0.50 if second_action.action == "answer" else 0.80 if second_action.action == "abstain" else 0.0
        if effect == "ambiguous_support":
            return 0.20 if second_action.action == "answer" else 0.95 if second_action.action == "abstain" else 0.0
        if effect == "insufficient":
            return 0.05 if second_action.action == "answer" else 1.0 if second_action.action == "abstain" else 0.0
        if effect == "residual_uncertainty":
            return 0.0 if second_action.action == "answer" else 1.0 if second_action.action == "abstain" else 0.0

    return 0.0


def score_final_policy(row, final_action: str, final_correct: bool) -> float:
    optimal_final = row["optimal_final_action"]

    if final_action == optimal_final:
        if final_action == "answer":
            return 1.0 if final_correct else 0.3
        return 1.0

    if optimal_final == "abstain" and final_action == "answer":
        return 0.0
    if optimal_final == "answer" and final_action == "abstain":
        return 0.4
    return 0.0


def proper_calibration_score(confidence: float, target_correct: bool) -> float:
    p = clamp(confidence)
    y = 1.0 if target_correct else 0.0
    return 1.0 - ((p - y) ** 2)


def score_confidence_dynamics(row, first_action: MetaAction, second_action: Optional[MetaAction]) -> float:
    if second_action is None:
        return 1.0

    c1 = clamp(first_action.confidence)
    c2 = clamp(second_action.confidence)

    if first_action.action == "ask_hint":
        if row["hint_effect"] == "resolve":
            return 1.0 if (c2 >= c1 and c2 <= 0.97) else 0.5
        if row["hint_effect"] == "partial":
            return 1.0 if c2 <= min(0.74, c1 + 0.05) else 0.2
        if row["hint_effect"] == "none":
            return 1.0 if c2 <= 0.68 else 0.1

    if first_action.action == "verify":
        ve = row["verify_effect"]
        if ve == "confirm":
            return 1.0 if (c2 >= c1 and c2 <= 0.97) else 0.5
        if ve == "weak_confirm":
            return 1.0 if c2 <= min(0.84, c1 + 0.08) else 0.25
        if ve == "warn":
            return 1.0 if c2 <= min(0.76, c1 + 0.03) else 0.15
        if ve == "ambiguous_support":
            return 1.0 if c2 <= 0.70 else 0.10
        if ve == "insufficient":
            return 1.0 if c2 <= 0.68 else 0.10
        if ve == "residual_uncertainty":
            return 1.0 if c2 <= 0.62 else 0.05

    return 0.8


def score_efficiency(row, first_action: MetaAction, second_action: Optional[MetaAction]) -> float:
    penalty = 0.0
    optimal = row["optimal_first_action"]

    if first_action.action == "ask_hint" and optimal != "ask_hint":
        penalty += 0.15
    if first_action.action == "verify" and optimal != "verify":
        penalty += 0.12
    if first_action.action == "answer" and optimal in {"ask_hint", "verify"}:
        penalty += 0.10
    if first_action.action == "abstain" and optimal == "answer":
        penalty += 0.12
    if second_action is not None and second_action.action in {"ask_hint", "verify"}:
        penalty += 0.20

    return clamp(1.0 - penalty)


def score_mc_intervene_v6_episode(row, first_action: MetaAction, second_action: Optional[MetaAction] = None) -> EpisodeResult:
    validate_meta_action(first_action)
    if second_action is not None:
        validate_meta_action(second_action)

    if first_action.action in {"answer", "abstain"}:
        final_action = first_action.action
        final_answer = first_action.answer
    else:
        final_action = second_action.action if second_action is not None else first_action.action
        final_answer = second_action.answer if second_action is not None else None

    outcome_score, final_correct, final_safe = outcome_score_from_final_state(
        row=row,
        final_action=final_action,
        final_answer=final_answer,
    )

    first_action_score = score_first_action(row, first_action)
    transition_score = score_transition(row, first_action, second_action)
    final_policy_score = score_final_policy(row, final_action, final_correct)

    control_score = (
        0.45 * first_action_score
        + 0.25 * transition_score
        + 0.30 * final_policy_score
    )

    calibration_ref = second_action if second_action is not None else first_action
    calibration_target = final_correct if final_action == "answer" else final_safe
    calibration_score = proper_calibration_score(calibration_ref.confidence, calibration_target)

    confidence_dynamics_score = score_confidence_dynamics(row, first_action, second_action)
    efficiency_score = score_efficiency(row, first_action, second_action)

    final_score = (
        0.35 * outcome_score
        + 0.30 * control_score
        + 0.15 * calibration_score
        + 0.10 * confidence_dynamics_score
        + 0.10 * efficiency_score
    )

    return EpisodeResult(
        item_id=row["item_id"],
        final_score=float(final_score),
        outcome_score=float(outcome_score),
        control_score=float(control_score),
        calibration_score=float(calibration_score),
        confidence_dynamics_score=float(confidence_dynamics_score),
        efficiency_score=float(efficiency_score),
        first_action=first_action.action,
        final_action=final_action,
        final_correct=bool(final_correct),
        final_safe=bool(final_safe),
    )