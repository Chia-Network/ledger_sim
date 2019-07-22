from ..atoms import hash_pointer, streamable, uint64

from .Hash import std_hash
from .Program import ProgramHash


@streamable
class Coin:
    """
    This structure is used in the body for the reward and fees genesis coins.
    """
    parent_coin_info: "CoinName"
    puzzle_hash: ProgramHash
    amount: uint64

    def name(self) -> "CoinName":
        return CoinName(self)


CoinName = hash_pointer(Coin, std_hash)

Coin.__annotations__["parent_coin_info"] = CoinName
