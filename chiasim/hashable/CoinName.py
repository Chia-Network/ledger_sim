from ..atoms import hash_pointer, streamable

from .Hash import std_hash
from .Program import ProgramHash


@streamable
class CoinNameData:
    """
    The elements that contribute to the name of a coin.
    """
    parent_coin_info: "CoinName"
    puzzle_hash: ProgramHash


CoinName = hash_pointer(CoinNameData, std_hash)

CoinNameData.__annotations__["parent_coin_info"] = CoinName
