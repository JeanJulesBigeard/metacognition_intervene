from __future__ import annotations

import random
from mc_intervene.generators.base import GeneratorBase
from mc_intervene.policy import derive_optimal_policy
from mc_intervene.schema import ItemRow

class IrrecoverableGenerator(GeneratorBase):
    def generate(self, rng: random.Random, idx: int, group_id: str) -> ItemRow:
        project = rng.choice(["Alpha", "Nova", "Helix", "Orion"])
        variant = rng.choices(
            population=[
                "true_abstain",
                "hint_resolves",
                "hint_partial",
                "verify_warn_only",
                "deceptive_recoverable_looking",
                "near_threshold_unknown",
            ],
            weights=[1, 1, 2, 4, 5, 5],
            k=1,
        )[0]

        if variant == "true_abstain":
            ground_truth = "unknown"
            hint_effect = "none"
            verify_effect = "insufficient"
            hint_payload = "The project finished before the deadline, but the bonus threshold is unavailable."
            payloads = {"insufficient": "The available records do not determine whether the bonus rule was met."}

        elif variant == "hint_resolves":
            ground_truth = "yes"
            hint_effect = "resolve"
            verify_effect = "weak_confirm"
            hint_payload = "The bonus is awarded to any project completed before the deadline, and this project finished before the deadline."
            payloads = {"weak_confirm": "The available summary is consistent with eligibility, though the rule is only briefly stated."}

        elif variant == "hint_partial":
            ground_truth = "unknown"
            hint_effect = "partial"
            verify_effect = "insufficient"
            hint_payload = "The bonus requires finishing early enough, but the qualifying margin is still unspecified."
            payloads = {"insufficient": "The available records still do not settle eligibility."}

        elif variant == "verify_warn_only":
            ground_truth = "unknown"
            hint_effect = "none"
            verify_effect = "warn"
            hint_payload = "No extra policy threshold information is available."
            payloads = {"warn": "Some projects finished before the deadline without qualifying for the bonus."}

        elif variant == "deceptive_recoverable_looking":
            ground_truth = "unknown"
            hint_effect = "partial"
            verify_effect = "residual_uncertainty"
            hint_payload = "The policy mentions projects completed sufficiently early may receive a bonus, but the exact threshold remains unstated."
            payloads = {"residual_uncertainty": "Eligibility looks plausible, but the review still does not establish it."}

        else:
            ground_truth = "unknown"
            hint_effect = "partial"
            verify_effect = "warn"
            hint_payload = "Projects can qualify when completed sufficiently before the deadline, but this record only states that the project finished before the deadline."
            payloads = {"warn": "Finishing before the deadline is not always enough to qualify for the bonus."}

        row = {
            "item_id": f"irrecoverable_{idx}",
            "paired_item_group": group_id,
            "task_family": "mc_intervene",
            "subtype": "irrecoverable_case",
            "variant": variant,
            "prompt_text": f"Project {project} finished before the deadline. Did it qualify for the bonus?",
            "ground_truth": ground_truth,
            "solvability_type": "irrecoverable",
            "hint_effect": hint_effect,
            "verify_effect": verify_effect,
            "hint_payload": hint_payload,
            "verification_payload_map": payloads,
            "difficulty_band": "medium",
            "generator_family": "bundle_irrecoverable",
        }
        row.update(derive_optimal_policy(row))
        return ItemRow(**row)