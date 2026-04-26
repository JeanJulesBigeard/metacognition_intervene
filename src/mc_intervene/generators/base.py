from __future__ import annotations

from abc import ABC, abstractmethod
import random
from mc_intervene.schema import ItemRow

class GeneratorBase(ABC):
    @abstractmethod
    def generate(self, rng: random.Random, idx: int, group_id: str) -> ItemRow:
        raise NotImplementedError