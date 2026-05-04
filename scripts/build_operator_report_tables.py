import argparse
import glob
import os
import pandas as pd


SCORE_COLS = [
    "final_score",
    "outcome_score",
    "intervention_value_alignment_score",
    "control_score",
    "calibration_score",
    "efficiency_score",
]

ACTION_ORDER = ["answer", "ask_hint", "verify", "abstain"]


def infer_model_name(path: str) -> str:
    base = os.path.basename(path)
    return base.replace(".csv", "").replace("__", ":")


def load_traces(per_item_dir: str) -> pd.DataFrame:
    frames = []
    for path in sorted(glob.glob(os.path.join(per_item_dir, "*.csv"))):
        df = pd.read_csv(path)
        if "model" not in df.columns:
            df.insert(0, "model", infer_model_name(path))
        frames.append(df)
    if not frames:
        raise FileNotFoundError(f"No CSV files found in {per_item_dir}")
    return pd.concat(frames, ignore_index=True)


def build_operator_scores(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (model, op), g in df.groupby(["model", "uncertainty_operator"]):
        row = {"model": model, "uncertainty_operator": op, "n": len(g)}
        for col in SCORE_COLS:
            row[col] = g[col].mean() if col in g.columns else float("nan")
        rows.append(row)
    out = pd.DataFrame(rows).sort_values(["model", "uncertainty_operator"])
    return out[[
        "model", "uncertainty_operator",
        "final_score", "outcome_score", "intervention_value_alignment_score",
        "control_score", "calibration_score", "efficiency_score",
        "n",
    ]]


def build_action_rates(df: pd.DataFrame, action_col: str) -> pd.DataFrame:
    actions = [a for a in ACTION_ORDER if a in df[action_col].unique()]
    rows = []
    for (model, op), g in df.groupby(["model", "uncertainty_operator"]):
        row = {"model": model, "uncertainty_operator": op, "n": len(g)}
        counts = g[action_col].value_counts(normalize=True)
        for a in actions:
            row[f"{a}_rate"] = counts.get(a, 0.0)
        rows.append(row)
    out = pd.DataFrame(rows).sort_values(["model", "uncertainty_operator"])
    rate_cols = [f"{a}_rate" for a in actions]
    return out[["model", "uncertainty_operator"] + rate_cols + ["n"]]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-item-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    df = load_traces(args.per_item_dir)
    print(f"Loaded {len(df)} rows across {df['model'].nunique()} models "
          f"and {df['uncertainty_operator'].nunique()} operators.")

    scores = build_operator_scores(df)
    first_action = build_action_rates(df, "first_action")
    final_action = build_action_rates(df, "final_action")

    scores_path       = os.path.join(args.out_dir, "operator_scores_by_model.csv")
    first_action_path = os.path.join(args.out_dir, "operator_first_action_rates_by_model.csv")
    final_action_path = os.path.join(args.out_dir, "operator_final_action_rates_by_model.csv")

    scores.to_csv(scores_path, index=False)
    first_action.to_csv(first_action_path, index=False)
    final_action.to_csv(final_action_path, index=False)

    print(f"Saved:\n  {scores_path}\n  {first_action_path}\n  {final_action_path}")

    # ── Quick diagnostic print ────────────────────────────────────────────────
    pd.set_option("display.float_format", "{:.3f}".format)
    pd.set_option("display.max_rows", 200)
    pd.set_option("display.width", 160)

    print("\n── Operator scores (mean final_score, pivot: model × operator) ──")
    pivot = scores.pivot(index="uncertainty_operator", columns="model", values="final_score")
    print(pivot.round(3).to_string())

    print("\n── First-action rates (ask_hint_rate, pivot: model × operator) ──")
    ah = first_action.pivot(index="uncertainty_operator", columns="model", values="ask_hint_rate")
    print(ah.round(3).to_string())

    print("\n── Final-action rates (abstain_rate, pivot: model × operator) ──")
    ab = final_action.pivot(index="uncertainty_operator", columns="model", values="abstain_rate")
    print(ab.round(3).to_string())


if __name__ == "__main__":
    main()
