import dataclasses

from .base import uint64
from .Coin import Coin
from .Signature import Signature

from .make_streamable import streamable
from .hash_pointer import hash_pointer


@dataclasses.dataclass
class Solution:
    val: bytes

    def as_bin(self):
        return self.val


@streamable
class Body:
    coinbase_signature: Signature
    coinbase_coin: Coin
    fees_coin: Coin
    solution_program_hash: hash_pointer(Solution)
    program_cost: uint64
    aggregated_solution_signature: Signature

# solution program is simply a bunch of bytes
