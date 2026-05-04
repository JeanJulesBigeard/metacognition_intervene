import argparse
import pandas as pd


def compute_score(row, scoring_mode: str) -> float:
    outcome = float(row["outcome_score"])
    iva = float(row["intervention_value_alignment_score"])
    control = float(row["control_score"])
    calibration = float(row["calibration_score"])
    efficiency = float(row["efficiency_score"])

    if scoring_mode == "v2_1_full":
        return (
            0.35 * outcome
            + 0.30 * iva
            + 0.20 * control
            + 0.10 * calibration
            + 0.05 * efficiency
        )

    if scoring_mode == "v2_1_no_iva":
        return (
            0.50 * outcome
            + 0.30 * control
            + 0.15 * calibration
            + 0.05 * efficiency
        )

    raise ValueError(f"Unknown scoring_mode: {scoring_mode}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument(
        "--scoring-mode",
        choices=["v2_1_full", "v2_1_no_iva"],
        required=True,
    )
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    df["rescored_final_score"] = df.apply(
        lambda r: compute_score(r, args.scoring_mode),
        axis=1,
    )

    summary = df[[
        "rescored_final_score",
        "outcome_score",
        "intervention_value_alignment_score",
        "control_score",
        "calibration_score",
        "efficiency_score",
        "final_correct",
        "final_safe",
    ]].mean().sort_index()

    print("\nOverall summary")
    print(summary)

    print("\nBy uncertainty_operator")
    print(
        df.groupby("uncertainty_operator")[[
            "rescored_final_score",
            "outcome_score",
            "intervention_value_alignment_score",
            "control_score",
            "calibration_score",
            "efficiency_score",
        ]]
        .mean()
        .sort_values("rescored_final_score", ascending=False)
    )

    df.to_csv(args.out, index=False)
    print(f"\nSaved rescored output to {args.out}")


if __name__ == "__main__":
    main()
