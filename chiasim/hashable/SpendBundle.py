import dataclasses

from .Coin import Coin
from .Signature import Signature
from .Solution import Solution

from typing import Tuple, List


@dataclasses.dataclass(frozen=True)
class SpendBundle:
    spends: List[Tuple[Coin, Solution]]
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

    def fees(self) -> int:
        return 0
