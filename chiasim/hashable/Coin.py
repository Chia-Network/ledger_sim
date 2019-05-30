from ..atoms import streamable, uint64

from .Hash import Hashable
from .CoinInfo import CoinInfoHash


@streamable
class Coin(Hashable):
    coin_info_hash: CoinInfoHash
    amount: uint64

    def additions(self, solution):
        # TODO: run the script and figure out what new coins are created
        return []
