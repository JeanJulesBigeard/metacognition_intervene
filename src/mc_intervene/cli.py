from __future__ import annotations

import argparse
from mc_intervene.generators.builder import build_mc_intervene_df
from mc_intervene.export import export_dataset

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-bundles", type=int, default=100)
    parser.add_argument("--seed", type=int, default=67)
    parser.add_argument("--out-dir", type=str, default="data/mc_intervene_dataset_v1")
    args = parser.parse_args()

    df = build_mc_intervene_df(n_bundles=args.n_bundles, seed=args.seed)
    export_dataset(df, out_dir=args.out_dir)
    print(f"Exported {len(df)} rows to {args.out_dir}")

if __name__ == "__main__":
    main()