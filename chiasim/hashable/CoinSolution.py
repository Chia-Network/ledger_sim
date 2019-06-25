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
    """
    This is a rather disparate data structure that validates coin transfers. It's generally populated
    with data from a different sources, since burned coins are identified by name, so it is built up
    more often that it is streamed.
    """
    coin: Coin
    solution: Program

    def conditions(self):
        return conditions_for_puzzle_hash_solution(self.coin.puzzle_hash, self.solution.code)

    def conditions_dict(self):
        return conditions_by_opcode(self.conditions())

    def additions(self):
        return created_outputs_for_conditions_dict(self.conditions_dict(), self.coin.coin_name())

    def hash_key_pairs(self):
        return hash_key_pairs_for_conditions_dict(self.conditions_dict())


CoinSolutionList = streamable_list(CoinSolution)
