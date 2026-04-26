from __future__ import annotations

from pathlib import Path
import json
import pandas as pd

def export_dataset(df: pd.DataFrame, out_dir: str, name: str = "mc_intervene_eval") -> None:
    path = Path(out_dir)
    path.mkdir(parents=True, exist_ok=True)

    df.to_csv(path / f"{name}.csv", index=False)

    metadata = {
        "name": name,
        "n_rows": len(df),
        "n_bundles": int(df["paired_item_group"].nunique()),
        "columns": list(df.columns),
    }
    with open(path / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)