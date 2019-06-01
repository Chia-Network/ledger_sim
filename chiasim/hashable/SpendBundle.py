import dataclasses

from .BLSSignature import BLSSignature
from .Coin import Coin
from .Solution import Solution

from typing import Tuple, List


@dataclasses.dataclass(frozen=True)
class SpendBundle:
    spends: List[Tuple[Coin, Solution]]
    aggregated_signature: BLSSignature

    @classmethod
    def aggregate(cls, spend_bundles):
        spends = []
        sigs = []
        for _ in spend_bundles:
            spends += _.spends
            sigs.append(_.aggregated_signature)
        aggregated_signature = BLSSignature.aggregate(sigs)
        return cls(spends, aggregated_signature)

    def additions(self):
        items = []
        for coin, s in self.spends:
            items += coin.additions(s)
        return tuple(items)

    def removals(self):
        return tuple(_[0] for _ in self.spends)

    def fees(self) -> int:
        return 0
