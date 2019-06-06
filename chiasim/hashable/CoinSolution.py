from ..atoms import streamable, streamable_list

from .Coin import Coin
from .Program import Program


@streamable
class CoinSolution:
    coin: Coin
    solution: Program

    def additions(self):
        # TODO: run the script and figure out what new coins are created
        return []


CoinSolutionList = streamable_list(CoinSolution)
