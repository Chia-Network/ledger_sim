from ..atoms import streamable, uint64

from .Hash import Hashable
from .CoinName import CoinName, CoinNameData
from .Program import ProgramHash


@streamable
class Coin(Hashable):
    parent_coin_info: CoinName
    puzzle_hash: ProgramHash
    amount: uint64

    def coin_name_data(self) -> CoinNameData:
        return CoinNameData(self.parent_coin_info, self.puzzle_hash)

    def coin_name(self) -> CoinName:
        return CoinName(self.coin_name_data())
