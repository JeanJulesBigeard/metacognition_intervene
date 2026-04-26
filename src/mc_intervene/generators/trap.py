from __future__ import annotations

import random
from mc_intervene.generators.base import GeneratorBase
from mc_intervene.policy import derive_optimal_policy
from mc_intervene.schema import ItemRow

class TrapGenerator(GeneratorBase):
    def generate(self, rng: random.Random, idx: int, group_id: str) -> ItemRow:
        x = rng.randint(100, 999)
        y = int(str(x)[::-1])

        variant = rng.choices(
            population=[
                "verify_confirm",
                "verify_weak_confirm",
                "careful_answer_ok",
                "verify_warn",
                "verify_residual_uncertainty",
                "ambiguous_support_case",
            ],
            weights=[1, 4, 1, 4, 3, 5],
            k=1,
        )[0]

        if variant == "verify_confirm":
            ground_truth = str(max(x, y))
            verify_effect = "confirm"
            prompt = f"Two values are listed in a compressed table: {x} and {y}. What is the larger value? A quick scan may be misleading."
            payloads = {"confirm": f"Verification confirms that the larger value is {ground_truth}."}

        elif variant == "verify_weak_confirm":
            ground_truth = str(max(x, y))
            verify_effect = "weak_confirm"
            prompt = f"Two values are listed in a compressed table: {x} and {y}. What is the larger value? The formatting is easy to misread."
            payloads = {"weak_confirm": "The quick check found no contradiction, but the formatting still invites care."}

        elif variant == "careful_answer_ok":
            ground_truth = str(max(x, y))
            verify_effect = "warn"
            prompt = f"Two values are listed: {x} and {y}. What is the larger value?"
            payloads = {"warn": "Careful full comparison is needed, though no inconsistency is evident."}

        elif variant == "verify_warn":
            ground_truth = str(max(x, y))
            verify_effect = "warn"
            prompt = f"Two values are shown in a cramped ledger: {x} and {y}. What is the larger value? A superficial read may be unsafe."
            payloads = {"warn": "The check highlights a common misread pattern, though a careful answer may still be recoverable."}

        elif variant == "ambiguous_support_case":
            ground_truth = "unknown"
            verify_effect = "ambiguous_support"
            prompt = f"Two values are shown in a cramped ledger: {x} and a partially obscured second value. What is the larger value? A superficial reading may be unsafe."
            payloads = {"ambiguous_support": "The review suggests one comparison is plausible, but the obscured formatting leaves unresolved alternatives."}

        else:
            ground_truth = "unknown"
            verify_effect = "residual_uncertainty"
            prompt = f"Two values are partially visible in a compressed table: {x} and a distorted second value. What is the larger value?"
            payloads = {"residual_uncertainty": "The check suggests one value may be incomplete, so a definitive comparison is unsafe."}

        row = {
            "item_id": f"trap_{idx}",
            "paired_item_group": group_id,
            "task_family": "mc_intervene",
            "subtype": "trap_case",
            "variant": variant,
            "prompt_text": prompt,
            "ground_truth": ground_truth,
            "solvability_type": "trap_case",
            "hint_effect": "partial",
            "verify_effect": verify_effect,
            "hint_payload": "Compare the full magnitudes rather than relying on superficial pattern matching.",
            "verification_payload_map": payloads,
            "difficulty_band": "medium",
            "generator_family": "bundle_trap",
        }
        row.update(derive_optimal_policy(row))
        return ItemRow(**row)