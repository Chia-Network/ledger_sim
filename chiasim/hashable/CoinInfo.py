import dataclasses

from .Hash import Hash
from .Streamable import Streamable


@dataclasses.dataclass(frozen=True)
class CoinInfo(Streamable):
    parent_coin_info_hash: Hash
    puzzle_hash: Hash
