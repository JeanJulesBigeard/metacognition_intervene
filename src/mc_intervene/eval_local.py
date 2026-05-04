from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional
import pandas as pd
from tqdm import tqdm

from mc_intervene.schema import MetaAction


@dataclass
class EvalRow:
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

def evaluate_dataframe(
    df: pd.DataFrame,
    policy_fn: Callable[[dict], tuple[MetaAction, Optional[MetaAction]]],
    score_episode_fn,
    show_progress: bool = True,
    **score_kwargs,
) -> pd.DataFrame:
    rows = []
    iterator = df.iterrows()
    if show_progress:
        iterator = tqdm(iterator, total=len(df), desc="Evaluating")

    for _, row in iterator:
        item = row.to_dict()
        try:
            first_action, second_action = policy_fn(item)
        except Exception as e:
            print(f"\n[SKIP] {item.get('item_id', '?')}: {e}")
            continue
        result = score_episode_fn(item, first_action, second_action, **score_kwargs)
        final_action_obj = second_action if second_action is not None and first_action.action not in {"answer", "abstain"} else first_action
        rows.append({
            "item_id": result.item_id,
            "final_score": result.final_score,
            "outcome_score": result.outcome_score,
            "control_score": result.control_score,
            "intervention_value_alignment_score": result.intervention_value_alignment_score,
            "calibration_score": result.calibration_score,
            "confidence_dynamics_score": result.confidence_dynamics_score,
            "efficiency_score": result.efficiency_score,
            "first_action": result.first_action,
            "first_answer": first_action.answer,
            "first_confidence": first_action.confidence,
            "second_action": second_action.action if second_action is not None else None,
            "second_answer": second_action.answer if second_action is not None else None,
            "second_confidence": second_action.confidence if second_action is not None else None,
            "final_action": result.final_action,
            "final_answer": final_action_obj.answer,
            "final_correct": result.final_correct,
            "final_safe": result.final_safe,
            "subtype": item["subtype"],
            "variant": item["variant"],
            "paired_item_group": item["paired_item_group"],
            "uncertainty_operator": item.get("uncertainty_operator"),
            "optimal_first_action": item["optimal_first_action"],
            "optimal_final_action": item["optimal_final_action"],
            "hint_effect": item.get("hint_effect"),
            "verify_effect": item.get("verify_effect"),
        })
    return pd.DataFrame(rows)

def summarize_results(results_df: pd.DataFrame) -> pd.Series:
    if results_df.empty:
        return pd.Series({"n_items": 0, "note": "all items skipped"})
    return pd.Series({
        "n_items": len(results_df),
        "mean_final_score": results_df["final_score"].mean(),
        "mean_outcome_score": results_df["outcome_score"].mean(),
        "mean_control_score": results_df["control_score"].mean(),
        "mean_calibration_score": results_df["calibration_score"].mean(),
        "mean_confidence_dynamics_score": results_df["confidence_dynamics_score"].mean(),
        "mean_efficiency_score": results_df["efficiency_score"].mean(),
        "final_correct_rate": results_df["final_correct"].mean(),
        "final_safe_rate": results_df["final_safe"].mean(),
    })