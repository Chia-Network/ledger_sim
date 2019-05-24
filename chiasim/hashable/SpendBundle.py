import dataclasses

from .base import uint64
from .Coin import Coin
from .Signature import Signature
from .Streamable import Streamable

from typing import Tuple, List


@dataclasses.dataclass(frozen=True)
class SpendBundle(Streamable):
    spends: List[Tuple[Coin, bytes]]
    aggregated_solution_signature: Signature

    def __add__(self, other):
        return SpendBundle(
            self.spends + other.spends,
            self.aggregated_solution_signature + other.aggregated_solution_signature)

    def additions(self):
        items = []
        for coin, s in self.spends:
            items += coin.additions(s)
        return items

    def removals(self):
        return tuple(_[0] for _ in self.spends)

    def fees(self) -> uint64:
        return uint64(0)
