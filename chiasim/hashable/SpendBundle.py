import dataclasses

import blspy

from .Coin import Coin
from .Signature import Signature
from .Solution import Solution

from typing import Tuple, List


ZERO_SIG = b"\0" * 32


@dataclasses.dataclass(frozen=True)
class SpendBundle:
    spends: List[Tuple[Coin, Solution]]
    aggregated_signature: blspy.PrependSignature

    @classmethod
    def aggregate(cls, spend_bundles):
        spends = []
        sigs = []
        for _ in spend_bundles:
            spends += _.spends
            if _.aggregated_signature != ZERO_SIG:
                sigs.append(_.aggregated_signature)
        if len(sigs):
            aggregated_signature = blspy.PrependSignature.aggregate(sigs)
        else:
            aggregated_signature = ZERO_SIG
        return cls(spends, aggregated_signature)

    def __add__(self, other):
        return self.aggregate([self, other])

    @classmethod
    def empty(cls):
        return SpendBundle([], ZERO_SIG)

    def additions(self):
        items = []
        for coin, s in self.spends:
            items += coin.additions(s)
        return items

    def removals(self):
        return tuple(_[0] for _ in self.spends)

    def fees(self) -> int:
        return 0
