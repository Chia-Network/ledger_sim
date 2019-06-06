from ..atoms import hash_pointer, streamable, uint64

from .Hash import Hashable, std_hash
from .CoinName import CoinName
from .Puzzle import Puzzle


@streamable
class Coin(Hashable):
    parent_coin_info: CoinName
    puzzle_hash: hash_pointer(Puzzle, std_hash)
    amount: uint64

    def name(self):
        return CoinName(self.parent_coin_info, self.puzzle_hash)
