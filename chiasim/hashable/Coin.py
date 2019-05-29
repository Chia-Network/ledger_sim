from .base import uint64
from .Hash import Hash
from .make_streamable import streamable
from .CoinInfo import CoinInfoHash

@streamable
class Coin:
    coin_info_hash: CoinInfoHash
    amount: uint64

    def additions(self, solution):
        # TODO: run the script and figure out what new coins are created
        return []
