import argparse
import pandas as pd

from mc_intervene.eval_local import evaluate_dataframe, summarize_results
from mc_intervene.local_model import OllamaPolicy
from mc_intervene.scoring import score_mc_intervene_v6_episode

SCORE_COLS = ["final_score", "outcome_score", "control_score",
              "calibration_score", "confidence_dynamics_score", "efficiency_score"]
ACTION_ORDER = ["answer", "ask_hint", "verify", "abstain"]


def _section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def print_diagnostics(results: pd.DataFrame) -> None:
    # ── 1. Overall summary ────────────────────────────────────────
    _section("Overall summary")
    print(summarize_results(results).to_string())
    if results.empty:
        print("\n  No items were scored — all responses were skipped.")
        return

    # ── 2. Scores by subtype ──────────────────────────────────────
    _section("Mean scores by subtype")
    print(results.groupby("subtype")[SCORE_COLS].mean().round(3).to_string())

    # ── 3. First-action distribution ─────────────────────────────
    _section("First-action distribution")
    counts = results["first_action"].value_counts()
    pct = (counts / len(results) * 100).round(1)
    dist = pd.DataFrame({"count": counts, "pct": pct})
    dist = dist.reindex([a for a in ACTION_ORDER if a in dist.index])
    print(dist.to_string())

    # ── 4. First-action confusion vs optimal ─────────────────────
    _section("First-action confusion  (rows = model, cols = optimal)")
    confusion_first = pd.crosstab(
        results["first_action"],
        results["optimal_first_action"],
        rownames=["model"],
        colnames=["optimal"],
        margins=True,
    )
    print(confusion_first.to_string())

    # ── 5. Final-action confusion vs optimal ─────────────────────
    _section("Final-action confusion  (rows = model, cols = optimal)")
    confusion_final = pd.crosstab(
        results["final_action"],
        results["optimal_final_action"],
        rownames=["model"],
        colnames=["optimal"],
        margins=True,
    )
    print(confusion_final.to_string())

    # ── 6. Scores by verify_effect ────────────────────────────────
    _section("Mean scores by verify_effect")
    ve = results.dropna(subset=["verify_effect"])
    if not ve.empty:
        print(ve.groupby("verify_effect")[SCORE_COLS].mean().round(3).to_string())
    else:
        print("  (no verify_effect data)")

    # ── 7. Scores by hint_effect ──────────────────────────────────
    _section("Mean scores by hint_effect")
    he = results.dropna(subset=["hint_effect"])
    if not he.empty:
        print(he.groupby("hint_effect")[SCORE_COLS].mean().round(3).to_string())
    else:
        print("  (no hint_effect data)")

    print(f"\n{'─' * 60}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--provider", default="ollama")
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url", default="http://localhost:11434")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()

    df = pd.read_csv(args.data)
    if args.limit:
        df = df.head(args.limit).copy()

    if args.provider == "ollama":
        policy = OllamaPolicy(model=args.model, base_url=args.base_url, timeout=args.timeout)
    else:
        raise ValueError(f"Unsupported provider: {args.provider}")

    if hasattr(policy, "warmup"):
        print("Warming up model...")
        policy.warmup()

    results = evaluate_dataframe(df, policy, score_mc_intervene_v6_episode)
    print_diagnostics(results)


if __name__ == "__main__":
    main()