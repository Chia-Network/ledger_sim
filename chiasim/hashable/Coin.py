import dataclasses

from .base import uint64
from .Hash import Hash
from .Streamable import Streamable


@dataclasses.dataclass(frozen=True)
class Coin(Streamable):
    coin_info_hash: Hash
    amount: uint64

    def additions(self, solution):
        # TODO: run the script and figure out what new coins are created
        return []
