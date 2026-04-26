from __future__ import annotations

import random
from mc_intervene.generators.base import GeneratorBase
from mc_intervene.policy import derive_optimal_policy
from mc_intervene.schema import ItemRow

class MissingGenerator(GeneratorBase):
    def generate(self, rng: random.Random, idx: int, group_id: str) -> ItemRow:
        a = rng.randint(15, 80)
        b = rng.randint(15, 80)
        hint_effect = rng.choice(["resolve", "partial", "none"])

        if hint_effect == "resolve":
            ground_truth = str(a + b)
            hint_payload = f"The missing Team B score is {b}."
            verify_effect = "weak_confirm"
            payloads = {"weak_confirm": "The recovered information is consistent with a single plausible total, though the check is not a formal proof."}
        elif hint_effect == "partial":
            ground_truth = "unknown"
            hint_payload = "The missing Team B score is between 20 and 40."
            verify_effect = "insufficient"
            payloads = {"insufficient": "The currently available information does not uniquely determine the answer."}
        else:
            ground_truth = "unknown"
            hint_payload = "The missing Team B score is not available."
            verify_effect = "insufficient"
            payloads = {"insufficient": "The currently available information does not uniquely determine the answer."}

        row = {
            "item_id": f"missing_{idx}",
            "paired_item_group": group_id,
            "task_family": "mc_intervene",
            "subtype": "missing_case",
            "variant": f"missing_{hint_effect}",
            "prompt_text": f"A report states that Team A scored {a} points and Team B scored an unknown number of points. What is the total score?",
            "ground_truth": ground_truth,
            "solvability_type": "recoverable_missing",
            "hint_effect": hint_effect,
            "verify_effect": verify_effect,
            "hint_payload": hint_payload,
            "verification_payload_map": payloads,
            "difficulty_band": "medium",
            "generator_family": "bundle_missing",
        }
        row.update(derive_optimal_policy(row))
        return ItemRow(**row)