from .Hash import Hash
from .make_streamable import streamable
from .hash_pointer import hash_pointer


@streamable
class CoinInfo:
    parent_coin_info: "CoinInfoHash"
    puzzle: Hash


CoinInfoHash = hash_pointer(CoinInfo)

CoinInfo.__annotations__["parent_coin_info"] = CoinInfoHash
