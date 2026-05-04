"""
Generate all Phase 8 report artifacts into outputs/phase8_report_<timestamp>/.

Usage:
    python scripts/build_phase8_tables.py \
        --phase8-dir outputs/eval_local_phase8_20260503_212137 \
        --degenerate-full-iva outputs/ablation_degenerate_full_iva.csv \
        --degenerate-no-iva   outputs/ablation_degenerate_no_iva.csv

Outputs:
    phase8_model_leaderboard.csv
    degenerate_baseline_table.csv
    iva_ablation_model_table.csv
    degenerate_iva_ablation_table.csv
    operator_scores_by_model.csv
    operator_first_action_rates_by_model.csv
    operator_final_action_rates_by_model.csv
"""

import argparse
import glob
import os
import sys
from datetime import datetime

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

DEGENERATE_INTERPRETATION = {
    "oracle":                "optimal trajectory; should remain near ceiling",
    "verify_then_answer":    "blind verify-first, answer-final heuristic",
    "verify_then_abstain":   "blind verify-first, abstain-final heuristic",
    "always_abstain":        "conservative final-policy heuristic",
    "ask_hint_then_abstain": "low-value help-seeking heuristic",
    "ask_hint_then_answer":  "blind hint-first, answer-final heuristic",
    "always_answer_yes":     "blind positive-answer heuristic",
    "always_answer_no":      "blind negative-answer heuristic",
    "direct_gold_answer":    "omniscient latent-truth cheat baseline",
}

FULL_IVA_WEIGHTS = dict(outcome=0.35, iva=0.30, control=0.20, calibration=0.10, efficiency=0.05)
NO_IVA_WEIGHTS  = dict(outcome=0.50,             control=0.30, calibration=0.15, efficiency=0.05)


# ── helpers ───────────────────────────────────────────────────────────────────

def infer_model(path: str) -> str:
    return os.path.basename(path).replace(".csv", "").replace("__", ":")


def load_per_item(per_item_dir: str) -> pd.DataFrame:
    frames = []
    for path in sorted(glob.glob(os.path.join(per_item_dir, "*.csv"))):
        df = pd.read_csv(path)
        if "model" not in df.columns:
            df.insert(0, "model", infer_model(path))
        frames.append(df)
    if not frames:
        raise FileNotFoundError(f"No CSVs in {per_item_dir}")
    return pd.concat(frames, ignore_index=True)


# ── table builders ────────────────────────────────────────────────────────────

def build_leaderboard(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for model, g in df.groupby("model"):
        rows.append({
            "model":               model,
            "final_score":         g["final_score"].mean(),
            "outcome_score":       g["outcome_score"].mean(),
            "iva_score":           g["intervention_value_alignment_score"].mean(),
            "control_score":       g["control_score"].mean(),
            "calibration_score":   g["calibration_score"].mean(),
            "efficiency_score":    g["efficiency_score"].mean(),
            "final_correct_rate":  g["final_correct"].mean(),
            "final_safe_rate":     g["final_safe"].mean(),
            "n":                   len(g),
        })
    return (pd.DataFrame(rows)
              .sort_values("final_score", ascending=False)
              .reset_index(drop=True))


def build_degenerate_baseline(degenerate_csv: str) -> pd.DataFrame:
    df = pd.read_csv(degenerate_csv)
    agg = (df.groupby("policy")
             .agg(
                 final_score=("final_score", "mean"),
                 outcome_score=("outcome_score", "mean"),
                 control_score=("control_score", "mean"),
                 iva_score=("intervention_value_alignment_score", "mean"),
                 calibration_score=("calibration_score", "mean"),
                 efficiency_score=("efficiency_score", "mean"),
                 final_correct=("final_correct", "mean"),
             )
             .reset_index())
    agg["interpretation"] = agg["policy"].map(DEGENERATE_INTERPRETATION).fillna("")
    return agg.sort_values("final_score", ascending=False).reset_index(drop=True)


def build_iva_ablation_model(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for model, g in df.groupby("model"):
        full = (FULL_IVA_WEIGHTS["outcome"]     * g["outcome_score"].mean()
              + FULL_IVA_WEIGHTS["iva"]         * g["intervention_value_alignment_score"].mean()
              + FULL_IVA_WEIGHTS["control"]     * g["control_score"].mean()
              + FULL_IVA_WEIGHTS["calibration"] * g["calibration_score"].mean()
              + FULL_IVA_WEIGHTS["efficiency"]  * g["efficiency_score"].mean())
        no_iva = (NO_IVA_WEIGHTS["outcome"]     * g["outcome_score"].mean()
                + NO_IVA_WEIGHTS["control"]     * g["control_score"].mean()
                + NO_IVA_WEIGHTS["calibration"] * g["calibration_score"].mean()
                + NO_IVA_WEIGHTS["efficiency"]  * g["efficiency_score"].mean())
        rows.append({
            "model":                model,
            "full_with_iva":        full,
            "no_iva":               no_iva,
            "delta_no_iva_minus_full": no_iva - full,
            "outcome_score":        g["outcome_score"].mean(),
            "iva_score":            g["intervention_value_alignment_score"].mean(),
            "control_score":        g["control_score"].mean(),
            "calibration_score":    g["calibration_score"].mean(),
            "efficiency_score":     g["efficiency_score"].mean(),
            "final_correct_rate":   g["final_correct"].mean(),
            "final_safe_rate":      g["final_safe"].mean(),
        })
    return (pd.DataFrame(rows)
              .sort_values("full_with_iva", ascending=False)
              .reset_index(drop=True))


def build_degenerate_iva_ablation(full_iva_csv: str, no_iva_csv: str) -> pd.DataFrame:
    agg_cols = {
        "final_score":                        "mean",
        "outcome_score":                      "mean",
        "intervention_value_alignment_score": "mean",
        "final_correct":                      "mean",
    }
    full  = (pd.read_csv(full_iva_csv)
               .groupby("policy").agg(agg_cols)
               .rename(columns={"final_score": "full_with_iva"}))
    noiva = (pd.read_csv(no_iva_csv)
               .groupby("policy").agg({"final_score": "mean"})
               .rename(columns={"final_score": "no_iva"}))
    out = full.join(noiva, how="inner").reset_index()
    out["delta_no_iva_minus_full"] = out["no_iva"] - out["full_with_iva"]
    out["interpretation"] = out["policy"].map(DEGENERATE_INTERPRETATION).fillna("")
    return (out[["policy", "full_with_iva", "no_iva", "delta_no_iva_minus_full",
                 "outcome_score", "intervention_value_alignment_score",
                 "final_correct", "interpretation"]]
              .sort_values("full_with_iva", ascending=False)
              .reset_index(drop=True))


def build_operator_scores(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (model, op), g in df.groupby(["model", "uncertainty_operator"]):
        row = {"model": model, "uncertainty_operator": op, "n": len(g)}
        for col in SCORE_COLS:
            row[col] = g[col].mean() if col in g.columns else float("nan")
        rows.append(row)
    out = pd.DataFrame(rows).sort_values(["model", "uncertainty_operator"])
    return out[["model", "uncertainty_operator",
                "final_score", "outcome_score", "intervention_value_alignment_score",
                "control_score", "calibration_score", "efficiency_score", "n"]]


def build_action_rates(df: pd.DataFrame, action_col: str) -> pd.DataFrame:
    present = [a for a in ACTION_ORDER if a in df[action_col].unique()]
    rows = []
    for (model, op), g in df.groupby(["model", "uncertainty_operator"]):
        row = {"model": model, "uncertainty_operator": op, "n": len(g)}
        counts = g[action_col].value_counts(normalize=True)
        for a in present:
            row[f"{a}_rate"] = counts.get(a, 0.0)
        rows.append(row)
    out = pd.DataFrame(rows).sort_values(["model", "uncertainty_operator"])
    rate_cols = [f"{a}_rate" for a in present]
    return out[["model", "uncertainty_operator"] + rate_cols + ["n"]]


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase8-dir", required=True,
                        help="Phase 8 run directory (contains per_item/ and v2_1_dev_degenerate_policies.csv)")
    parser.add_argument("--degenerate-full-iva", required=True,
                        help="Per-item CSV scored with v2_1_full (for IVA ablation)")
    parser.add_argument("--degenerate-no-iva", required=True,
                        help="Per-item CSV scored with v2_1_no_iva (for IVA ablation)")
    parser.add_argument("--out-dir", default=None,
                        help="Output directory (default: outputs/phase8_report_<timestamp>)")
    args = parser.parse_args()

    if args.out_dir is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.out_dir = os.path.join("outputs", f"phase8_report_{ts}")
    os.makedirs(args.out_dir, exist_ok=True)

    per_item_dir   = os.path.join(args.phase8_dir, "per_item")
    degenerate_csv = os.path.join(args.phase8_dir, "v2_1_dev_degenerate_policies.csv")

    for p in [per_item_dir, degenerate_csv, args.degenerate_full_iva, args.degenerate_no_iva]:
        if not os.path.exists(p):
            print(f"ERROR: not found: {p}", file=sys.stderr)
            sys.exit(1)

    print(f"Loading per-item traces from {per_item_dir} …")
    traces = load_per_item(per_item_dir)
    print(f"  {len(traces)} rows, {traces['model'].nunique()} models, "
          f"{traces['uncertainty_operator'].nunique()} operators")

    tables = {
        "phase8_model_leaderboard":              build_leaderboard(traces),
        "degenerate_baseline_table":             build_degenerate_baseline(degenerate_csv),
        "iva_ablation_model_table":              build_iva_ablation_model(traces),
        "degenerate_iva_ablation_table":         build_degenerate_iva_ablation(
                                                     args.degenerate_full_iva,
                                                     args.degenerate_no_iva),
        "operator_scores_by_model":              build_operator_scores(traces),
        "operator_first_action_rates_by_model":  build_action_rates(traces, "first_action"),
        "operator_final_action_rates_by_model":  build_action_rates(traces, "final_action"),
    }

    saved = []
    for name, tbl in tables.items():
        path = os.path.join(args.out_dir, f"{name}.csv")
        tbl.to_csv(path, index=False)
        saved.append(path)

    print(f"\nSaved {len(saved)} tables to {args.out_dir}/")
    for p in saved:
        print(f"  {os.path.basename(p)}")

    # ── quick diagnostic summary ──────────────────────────────────────────────
    pd.set_option("display.float_format", "{:.4f}".format)
    pd.set_option("display.width", 160)

    print("\n── Model leaderboard ──")
    lb = tables["phase8_model_leaderboard"]
    print(lb[["model", "final_score", "outcome_score", "iva_score",
              "final_correct_rate"]].to_string(index=False))

    print("\n── Degenerate baselines (final_score) ──")
    dg = tables["degenerate_baseline_table"]
    print(dg[["policy", "final_score", "outcome_score", "interpretation"]].to_string(index=False))

    print("\n── IVA ablation (model) ──")
    ia = tables["iva_ablation_model_table"]
    print(ia[["model", "full_with_iva", "no_iva", "delta_no_iva_minus_full"]].to_string(index=False))

    print("\n── IVA ablation (degenerate) ──")
    da = tables["degenerate_iva_ablation_table"]
    print(da[["policy", "full_with_iva", "no_iva", "delta_no_iva_minus_full",
              "intervention_value_alignment_score"]].to_string(index=False))


if __name__ == "__main__":
    main()
