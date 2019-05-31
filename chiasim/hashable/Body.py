from ..atoms import hash_pointer, hexbytes, streamable, uint64

from .Coin import Coin
from .Hash import std_hash
from .Signature import Signature
from .Solution import Solution


@streamable
class Body:
    coinbase_signature: Signature
    coinbase_coin: Coin
    fees_coin: Coin
    solution_program: hash_pointer(Solution, std_hash)
    program_cost: uint64
    aggregated_signature: Signature
