from __future__ import annotations

import argparse

from mc_intervene.generators.builder import build_mc_intervene_df
from mc_intervene.generators.policy_v2 import build_policy_v2_df
from mc_intervene.export import export_dataset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset-version",
        choices=["v1", "policy_v2"],
        default="v1",
    )
    parser.add_argument("--n-bundles", type=int, default=100)
    parser.add_argument("--seed", type=int, default=67)
    parser.add_argument("--out-dir", type=str, default="data/mc_intervene_dataset")
    parser.add_argument("--name", type=str, default=None)
    parser.add_argument("--strict-validation", action="store_true")
    args = parser.parse_args()

    if args.dataset_version == "v1":
        df = build_mc_intervene_df(
            n_bundles=args.n_bundles,
            seed=args.seed,
        )
        default_name = "mc_intervene_eval"

    elif args.dataset_version == "policy_v2":
        df = build_policy_v2_df(
            n_bundles=args.n_bundles,
            seed=args.seed,
            validate=True,
            strict_validation=args.strict_validation,
        )
        default_name = "mc_intervene_policy_v2"

    else:
        raise ValueError(args.dataset_version)

    export_dataset(
        df,
        out_dir=args.out_dir,
        name=args.name or default_name,
    )

    print(f"Exported {len(df)} rows to {args.out_dir}")


if __name__ == "__main__":
    main()
