from ..atoms import streamable, uint64

from .Hash import Hashable
from .CoinInfo import CoinInfoHash


@streamable
class Coin(Hashable):
    coin_info_hash: CoinInfoHash
    amount: uint64
