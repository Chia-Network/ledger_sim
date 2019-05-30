from ..atoms import hash_pointer, hexbytes, streamable, uint64

from .Coin import Coin
from .Signature import Signature
from .Hash import std_hash


@streamable
class Body:
    coinbase_signature: Signature
    coinbase_coin: Coin
    fees_coin: Coin
    solution_program_hash: hash_pointer(hexbytes, std_hash)
    program_cost: uint64
    aggregated_solution_signature: Signature
