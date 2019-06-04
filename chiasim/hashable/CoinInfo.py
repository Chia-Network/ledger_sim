from ..atoms import hash_pointer, streamable

from .Hash import std_hash
from .Puzzle import Puzzle


@streamable
class CoinInfo:
    parent_coin_info: "CoinInfoHash"
    puzzle_hash: hash_pointer(Puzzle, std_hash)


CoinInfoHash = hash_pointer(CoinInfo, std_hash)

CoinInfo.__annotations__["parent_coin_info"] = CoinInfoHash
