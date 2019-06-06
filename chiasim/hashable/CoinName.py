from ..atoms import hash_pointer, streamable

from .Hash import std_hash
from .Puzzle import Puzzle


@streamable
class CoinNameData:
    parent_coin_info: "CoinName"
    puzzle_hash: hash_pointer(Puzzle, std_hash)


CoinName = hash_pointer(CoinNameData, std_hash)

CoinNameData.__annotations__["parent_coin_info"] = CoinName
