from ..atoms import streamable

from .BLSSignature import BLSSignature
from .CoinSolution import CoinSolutionList


@streamable
class SpendBundle:
    coin_solutions: CoinSolutionList
    aggregated_signature: BLSSignature

    @classmethod
    def aggregate(cls, spend_bundles):
        coin_solutions = []
        sigs = []
        for _ in spend_bundles:
            coin_solutions += _.coin_solutions
            sigs.append(_.aggregated_signature)
        aggregated_signature = BLSSignature.aggregate(sigs)
        return cls(coin_solutions, aggregated_signature)

    def additions(self):
        items = []
        for coin, s in self.coin_solutions:
            items += coin.additions(s)
        return tuple(items)

    def removals(self):
        return tuple(_[0] for _ in self.coin_solutions)

    def fees(self) -> int:
        return 0
