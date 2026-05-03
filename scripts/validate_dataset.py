import argparse
import pandas as pd

from mc_intervene.validation import validate_dataset


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--strict-bundle-operators", action="store_true")
    parser.add_argument("--require-rich-action-diversity", action="store_true")
    parser.add_argument("--min-effect-count", type=int, default=10)
    args = parser.parse_args()

    df = pd.read_csv(args.data)

    report = validate_dataset(
        df,
        strict_bundle_operators=args.strict_bundle_operators,
        require_rich_action_diversity=args.require_rich_action_diversity,
        min_effect_count=args.min_effect_count,
    )

    print("=" * 80)
    print("DATASET VALIDATION REPORT")
    print("=" * 80)
    print(f"Rows:    {report.n_rows}")
    print(f"Bundles: {report.n_bundles}")
    print(f"Passed:  {report.passed}")

    if report.warnings:
        print(f"\nWarnings ({len(report.warnings)}):")
        for warning in report.warnings:
            print(f"  [WARNING] {warning}")

    if report.errors:
        print(f"\nErrors ({len(report.errors)}):")
        for error in report.errors:
            print(f"  [ERROR] {error}")

    report.raise_if_failed()
    print("\nValidation passed.")


if __name__ == "__main__":
    main()
