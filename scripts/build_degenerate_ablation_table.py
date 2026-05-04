import argparse
import pandas as pd


INTERPRETATION = {
    "oracle":               "optimal trajectory; should remain near ceiling",
    "verify_then_answer":   "blind verify-first, answer-final heuristic",
    "verify_then_abstain":  "blind verify-first, abstain-final heuristic",
    "always_abstain":       "conservative final-policy heuristic",
    "ask_hint_then_abstain": "low-value help-seeking heuristic",
    "ask_hint_then_answer":  "blind hint-first, answer-final heuristic",
    "always_answer_yes":    "blind positive-answer heuristic",
    "always_answer_no":     "blind negative-answer heuristic",
    "direct_gold_answer":   "omniscient latent-truth cheat baseline",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full-iva", required=True, help="CSV from eval_degenerate_policies --scoring-mode v2_1_full")
    parser.add_argument("--no-iva",   required=True, help="CSV from eval_degenerate_policies --scoring-mode v2_1_no_iva")
    parser.add_argument("--out",      required=True)
    args = parser.parse_args()

    agg_cols = {
        "final_score":                        "mean",
        "outcome_score":                      "mean",
        "intervention_value_alignment_score": "mean",
        "final_correct":                      "mean",
    }

    full  = pd.read_csv(args.full_iva).groupby("policy").agg(agg_cols).rename(columns={"final_score": "full_with_iva"})
    noiva = pd.read_csv(args.no_iva).groupby("policy").agg({"final_score": "mean"}).rename(columns={"final_score": "no_iva"})

    out = full.join(noiva, how="inner").reset_index()
    out["delta_no_iva_minus_full"] = out["no_iva"] - out["full_with_iva"]
    out["interpretation"] = out["policy"].map(INTERPRETATION).fillna("")

    out = out[[
        "policy",
        "full_with_iva",
        "no_iva",
        "delta_no_iva_minus_full",
        "outcome_score",
        "intervention_value_alignment_score",
        "final_correct",
        "interpretation",
    ]].sort_values("full_with_iva", ascending=False)

    pd.set_option("display.float_format", "{:.4f}".format)
    pd.set_option("display.max_colwidth", 60)
    pd.set_option("display.width", 160)
    print(out.to_string(index=False))

    out.to_csv(args.out, index=False)
    print(f"\nSaved to {args.out}")


if __name__ == "__main__":
    main()
