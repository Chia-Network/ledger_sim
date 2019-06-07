from ..atoms import streamable, streamable_list
from ..coin.Conditions import conditions_by_opcode
from ..coin.consensus import (
    conditions_for_puzzle_hash_solution,
    created_outputs_for_conditions_dict,
    hash_key_pairs_for_conditions_dict
)

from .Coin import Coin
from .Program import Program


@streamable
class CoinSolution:
    coin: Coin
    solution: Program

    def conditions(self):
        return conditions_for_puzzle_hash_solution(self.coin.puzzle_hash, self.solution)

    def conditions_dict(self):
        return conditions_by_opcode(self.conditions())

    def additions(self):
        return created_outputs_for_conditions_dict(self.conditions(self.coin.coin_name()))

    def hash_key_pairs(self):
        return hash_key_pairs_for_conditions_dict(self.conditions_dict())


CoinSolutionList = streamable_list(CoinSolution)
