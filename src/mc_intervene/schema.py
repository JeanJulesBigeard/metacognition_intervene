from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field, ConfigDict

ActionType = Literal["answer", "ask_hint", "verify", "abstain"]
HintEffect = Literal["resolve", "partial", "none"]
VerifyEffect = Literal[
    "confirm",
    "weak_confirm",
    "warn",
    "ambiguous_support",
    "insufficient",
    "residual_uncertainty",
]

class MetaAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: ActionType
    answer: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    rationale_short: str

class ItemRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    paired_item_group: str
    task_family: str
    subtype: str
    variant: str
    prompt_text: str
    ground_truth: str
    solvability_type: str
    hint_effect: HintEffect
    verify_effect: VerifyEffect
    hint_payload: str
    verification_payload_map: dict[str, str]
    optimal_first_action: str
    acceptable_first_actions: list[str]
    optimal_final_action: str
    difficulty_band: str
    generator_family: str

    def to_task_record(self) -> dict:
        payload = self.verification_payload_map[self.verify_effect]
        d = self.model_dump()
        d["verification_payload"] = payload
        del d["verification_payload_map"]
        return d