from .base import uint64, hexbytes
from .Coin import Coin
from .Signature import Signature

from .make_streamable import streamable
from .hash_pointer import hash_pointer


@streamable
class Body:
    coinbase_signature: Signature
    coinbase_coin: Coin
    fees_coin: Coin
    solution_program_hash: hash_pointer(hexbytes)
    program_cost: uint64
    aggregated_solution_signature: Signature

# solution program is simply a bunch of bytes
