import argparse
import pandas as pd

from mc_intervene.schema import MetaAction
from mc_intervene.scoring import score_mc_intervene_v6_episode, ScoringMode
from mc_intervene.eval_local import summarize_results


def action(name, answer=None, confidence=0.5):
    return MetaAction(
        action=name,
        answer=answer,
        confidence=confidence,
        rationale_short="degenerate baseline",
    )


def policy_always_answer_yes(row):
    return action("answer", answer="yes", confidence=0.8), None


def policy_always_answer_no(row):
    return action("answer", answer="no", confidence=0.8), None


def policy_always_answer(row):
    return action("answer", answer=str(row["ground_truth"]), confidence=0.9), None


def policy_always_abstain(row):
    return action("abstain", confidence=0.8), None


def policy_ask_hint_then_abstain(row):
    return action("ask_hint", confidence=0.6), action("abstain", confidence=0.7)


def policy_ask_hint_then_answer(row):
    return action("ask_hint", confidence=0.6), action("answer", answer=str(row["ground_truth"]), confidence=0.8)


def policy_verify_then_abstain(row):
    return action("verify", confidence=0.6), action("abstain", confidence=0.7)


def policy_verify_then_answer(row):
    return action("verify", confidence=0.6), action("answer", answer=str(row["ground_truth"]), confidence=0.8)


def policy_oracle(row):
    first = row["optimal_first_action"]
    final = row["optimal_final_action"]

    first_action = action(
        first,
        answer=str(row["ground_truth"]) if first == "answer" else None,
        confidence=0.95,
    )

    if first in {"answer", "abstain"}:
        return first_action, None

    second_action = action(
        final,
        answer=str(row["ground_truth"]) if final == "answer" else None,
        confidence=0.95,
    )
    return first_action, second_action


POLICIES = {
    "always_answer_yes": policy_always_answer_yes,
    "always_answer_no": policy_always_answer_no,
    "direct_gold_answer": policy_always_answer,
    "always_abstain": policy_always_abstain,
    "ask_hint_then_abstain": policy_ask_hint_then_abstain,
    "ask_hint_then_answer": policy_ask_hint_then_answer,
    "verify_then_abstain": policy_verify_then_abstain,
    "verify_then_answer": policy_verify_then_answer,
    "oracle": policy_oracle,
}


def evaluate_policy(df, name, fn, scoring_mode: ScoringMode = "v2_1_full"):
    rows = []
    for _, row in df.iterrows():
        item = row.to_dict()
        first, second = fn(item)
        result = score_mc_intervene_v6_episode(item, first, second, scoring_mode=scoring_mode)
        rows.append({
            "policy": name,
            "item_id": result.item_id,
            "final_score": result.final_score,
            "outcome_score": result.outcome_score,
            "control_score": result.control_score,
            "intervention_value_alignment_score": result.intervention_value_alignment_score,
            "calibration_score": result.calibration_score,
            "confidence_dynamics_score": result.confidence_dynamics_score,
            "efficiency_score": result.efficiency_score,
            "final_correct": result.final_correct,
            "final_safe": result.final_safe,
            "first_action": result.first_action,
            "final_action": result.final_action,
            "optimal_first_action": item["optimal_first_action"],
            "optimal_final_action": item["optimal_final_action"],
            "verify_effect": item["verify_effect"],
            "hint_effect": item["hint_effect"],
            "uncertainty_operator": item["uncertainty_operator"],
        })
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", default=None)
    parser.add_argument(
        "--scoring-mode",
        choices=["v2_1_full", "v2_1_no_iva"],
        default="v2_1_full",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.data)

    all_results = []
    for name, fn in POLICIES.items():
        results = evaluate_policy(df, name, fn, scoring_mode=args.scoring_mode)
        all_results.append(results)

    out = pd.concat(all_results, ignore_index=True)

    summary = out.groupby("policy")[[
        "final_score",
        "outcome_score",
        "intervention_value_alignment_score",
        "control_score",
        "calibration_score",
        "confidence_dynamics_score",
        "efficiency_score",
        "final_correct",
        "final_safe",
    ]].mean().sort_values("final_score", ascending=False)

    print(summary)

    print("\nBy policy and optimal_first_action:")
    print(out.groupby(["policy", "optimal_first_action"])["final_score"].mean())

    if args.out:
        out.to_csv(args.out, index=False)
        print(f"\nSaved detailed results to {args.out}")


if __name__ == "__main__":
    main()
