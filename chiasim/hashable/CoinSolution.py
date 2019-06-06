from ..atoms import streamable, streamable_list

from .Coin import Coin
from .Solution import Solution


@streamable
class CoinSolution:
    coin: Coin
    solution: Solution

    def additions(self):
        # TODO: run the script and figure out what new coins are created
        return []


CoinSolutionList = streamable_list(CoinSolution)
