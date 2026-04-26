from __future__ import annotations

import random
import pandas as pd
from mc_intervene.generators.direct import DirectGenerator
from mc_intervene.generators.missing import MissingGenerator
from mc_intervene.generators.trap import TrapGenerator
from mc_intervene.generators.irrecoverable import IrrecoverableGenerator

def build_mc_intervene_df(n_bundles: int = 100, seed: int = 67) -> pd.DataFrame:
    rng = random.Random(seed)
    direct = DirectGenerator()
    missing = MissingGenerator()
    trap = TrapGenerator()
    irrecoverable = IrrecoverableGenerator()

    rows = []
    for i in range(n_bundles):
        group_id = f"bundle_{i}"
        rows.append(direct.generate(rng, i, group_id).to_task_record())
        rows.append(missing.generate(rng, i, group_id).to_task_record())
        rows.append(trap.generate(rng, i, group_id).to_task_record())
        rows.append(irrecoverable.generate(rng, i, group_id).to_task_record())
    return pd.DataFrame(rows)