from __future__ import annotations

import random
from mc_intervene.generators.base import GeneratorBase
from mc_intervene.policy import derive_optimal_policy
from mc_intervene.schema import ItemRow

class DirectGenerator(GeneratorBase):
    def generate(self, rng: random.Random, idx: int, group_id: str) -> ItemRow:
        a = rng.randint(20, 80)
        b = rng.randint(20, 80)

        variant = rng.choices(
            population=["clean_exact", "tempt_verify", "precision_mismatch", "cautious_wording", "rounded_report"],
            weights=[1, 2, 3, 2, 3],
            k=1,
        )[0]

        if variant == "clean_exact":
            ground_truth = str(a + b)
            solvability_type = "solvable_direct"
            verify_effect = "confirm"
            prompt = f"A report states that Team A scored {a} points and Team B scored {b} points. What is the total score?"
            payloads = {"confirm": f"The reported total is consistent with {ground_truth}."}

        elif variant == "tempt_verify":
            ground_truth = str(a + b)
            solvability_type = "solvable_direct"
            verify_effect = "weak_confirm"
            prompt = f"A report states that Team A scored {a} points and Team B scored {b} points. What is the total score? The formatting invites careful checking."
            payloads = {"weak_confirm": "No inconsistency was found, though the formatting still warrants care."}

        elif variant == "precision_mismatch":
            ground_truth = "unknown"
            solvability_type = "irrecoverable"
            verify_effect = "insufficient"
            prompt = f"A report states that Team A scored {a} points and Team B scored approximately {b} points. What is the exact total score?"
            payloads = {"insufficient": "The report supports an approximate total, not an exact one."}

        elif variant == "cautious_wording":
            ground_truth = str(a + b)
            solvability_type = "solvable_direct"
            verify_effect = "warn"
            prompt = f"A record lists Team A at {a} points and Team B at {b} points. What total was recorded? Read carefully before committing."
            payloads = {"warn": "The record appears consistent, but cautious interpretation is still advisable."}

        else:
            ground_truth = "unknown"
            solvability_type = "irrecoverable"
            verify_effect = "residual_uncertainty"
            prompt = f"A report lists Team A at about {a} points and Team B at about {b} points. What exact total was recorded?"
            payloads = {"residual_uncertainty": "The report only supports an approximate combined total, not an exact recorded value."}

        row = {
            "item_id": f"direct_{idx}",
            "paired_item_group": group_id,
            "task_family": "mc_intervene",
            "subtype": "direct_case",
            "variant": variant,
            "prompt_text": prompt,
            "ground_truth": ground_truth,
            "solvability_type": solvability_type,
            "hint_effect": "none",
            "verify_effect": verify_effect,
            "hint_payload": "No hidden numeric field is available beyond the text.",
            "verification_payload_map": payloads,
            "difficulty_band": "easy" if variant == "clean_exact" else "medium",
            "generator_family": "bundle_direct",
        }
        row.update(derive_optimal_policy(row))
        return ItemRow(**row)