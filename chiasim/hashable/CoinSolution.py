from ..atoms import streamable, streamable_list, uint64

from .CoinInfo import CoinInfo
from .Hash import Hash
from .Solution import Solution


@streamable
class CoinSolution:
    parent_coin_info: CoinInfo
    puzzle_hash: Hash
    amount: uint64
    solution: Solution

    def additions(self):
        # TODO: run the script and figure out what new coins are created
        return []


CoinSolutionList = streamable_list(CoinSolution)
