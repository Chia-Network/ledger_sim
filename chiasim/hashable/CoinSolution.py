from ..atoms import streamable, streamable_list
from ..coin.consensus import (
    conditions_for_puzzle_hash_solution,
    created_outputs_for_conditions,
    hash_key_pairs_for_condition
)

from .Coin import Coin
from .Program import Program


@streamable
class CoinSolution:
    coin: Coin
    solution: Program

    def conditions(self):
        return conditions_for_puzzle_hash_solution(self.coin.puzzle_hash, self.solution)

    def additions(self):
        return created_outputs_for_conditions(self.conditions(self.coin.coin_name()))

    def hash_key_pairs(self):
        return hash_key_pairs_for_condition(self.conditions())


CoinSolutionList = streamable_list(CoinSolution)
