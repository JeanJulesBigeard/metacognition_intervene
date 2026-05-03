"""
Audit resolve-hint cases: check that hint payloads are operationally clear and
sufficient to derive a deterministic answer.
"""

import argparse
import textwrap

import pandas as pd


DIVIDER = "=" * 80
SUBDIV = "-" * 60


def fmt(label: str, text: str, width: int = 76) -> str:
    wrapped = textwrap.fill(str(text), width=width, subsequent_indent="    ")
    return f"  [{label}]\n    {wrapped}\n"


def audit_row(i: int, row: dict) -> None:
    print(DIVIDER)
    print(f"  #{i+1}  item_id: {row['item_id']}")
    print(f"       operator: {row['uncertainty_operator']}  |  hint_effect: {row['hint_effect']}  |  verify_effect: {row['verify_effect']}")
    print(f"       optimal_first: {row['optimal_first_action']}  →  optimal_final: {row['optimal_final_action']}  |  ground_truth: {row['ground_truth']}")
    print(SUBDIV)
    print(fmt("PROMPT", row["prompt_text"], width=76))
    print(fmt("HINT PAYLOAD", row["hint_payload"]))
    print(fmt("VERIFY PAYLOAD", row["verification_payload"]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to dataset CSV")
    parser.add_argument("--n", type=int, default=20, help="Number of rows to show")
    parser.add_argument("--operator", default=None, help="Filter by uncertainty_operator")
    args = parser.parse_args()

    df = pd.read_csv(args.data)

    resolve = df[df["hint_effect"] == "resolve"].copy()

    if args.operator:
        resolve = resolve[resolve["uncertainty_operator"] == args.operator]

    print(f"\nTotal hint_effect=resolve rows: {len(resolve)}")
    print("Operator breakdown:")
    print(resolve["uncertainty_operator"].value_counts().to_string())
    print()

    sample = resolve.sample(n=min(args.n, len(resolve)), random_state=42)

    for i, (_, row) in enumerate(sample.iterrows()):
        audit_row(i, row.to_dict())

    print(DIVIDER)
    print(f"\nShown {len(sample)} of {len(resolve)} resolve-hint rows.")


if __name__ == "__main__":
    main()
