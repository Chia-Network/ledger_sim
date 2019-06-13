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
        for coin_solution in self.coin_solutions._items:
            items += coin_solution.additions()
        return tuple(items)

    def removals(self):
        return tuple(_.coin for _ in self.coin_solutions)

    def fees(self) -> int:
        amount_in = sum(_.amount for _ in self.removals())
        amount_out = sum(_.amount for _ in self.additions())
        return amount_in - amount_out

    def validate_signature(self) -> bool:
        hash_key_pairs = []
        for coin_solution in self.coin_solutions:
            hash_key_pairs += coin_solution.hash_key_pairs()
        return self.aggregated_signature.validate(hash_key_pairs)
