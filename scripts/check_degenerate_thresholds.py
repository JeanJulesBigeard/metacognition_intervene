"""
Release gate: verify that no degenerate baseline policy exceeds its score ceiling.

Exit code 0 → all policies are within threshold (safe to release).
Exit code 1 → one or more policies breach their threshold (block release).

Usage:
    python scripts/check_degenerate_thresholds.py
    python scripts/check_degenerate_thresholds.py --data outputs/v2_dev_degenerate_policies.csv
"""

import argparse
import sys

import pandas as pd


THRESHOLDS: dict[str, float] = {
    "always_abstain":        0.40,
    "always_answer_yes":     0.45,
    "always_answer_no":      0.45,
    "ask_hint_then_abstain": 0.40,
    "verify_then_abstain":   0.45,
    "verify_then_answer":    0.55,
}

DEFAULT_DATA = "outputs/v2_dev_degenerate_policies.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data",
        default=DEFAULT_DATA,
        help=f"Path to degenerate policy scores CSV (default: {DEFAULT_DATA})",
    )
    args = parser.parse_args()

    try:
        df = pd.read_csv(args.data)
    except FileNotFoundError:
        print(f"ERROR: file not found: {args.data}", file=sys.stderr)
        print(
            "Run `python scripts/eval_degenerate_policies.py --data <dataset.csv> "
            f"--out {args.data}` first.",
            file=sys.stderr,
        )
        sys.exit(1)

    mean_scores = df.groupby("policy")["final_score"].mean()

    failures: list[str] = []
    rows: list[tuple[str, float, float, str]] = []

    for policy, ceiling in sorted(THRESHOLDS.items()):
        if policy not in mean_scores.index:
            print(f"  MISSING  {policy:<28} (not found in data, skipping)")
            continue
        score = float(mean_scores[policy])
        status = "PASS" if score <= ceiling else "FAIL"
        rows.append((status, score, ceiling, policy))
        if status == "FAIL":
            failures.append(
                f"  {policy}: score={score:.4f} exceeds ceiling={ceiling:.2f}"
            )

    print(f"\nDegenerate policy gate — {args.data}\n")
    print(f"  {'STATUS':<6}  {'SCORE':>7}  {'CEILING':>7}  POLICY")
    print(f"  {'------':<6}  {'-------':>7}  {'-------':>7}  ------")
    for status, score, ceiling, policy in rows:
        marker = " ✓" if status == "PASS" else " ✗"
        print(f"  {status:<6}  {score:>7.4f}  {ceiling:>7.2f}  {policy}{marker}")

    if failures:
        print(f"\n[FAIL] {len(failures)} threshold(s) breached:")
        for msg in failures:
            print(msg)
        sys.exit(1)

    print(f"\n[PASS] All {len(rows)} policies within threshold.")
    sys.exit(0)


if __name__ == "__main__":
    main()
