from ..atoms import hash_pointer, streamable, uint64

from .BLSSignature import BLSSignature
from .Coin import Coin
from .Hash import std_hash
from .Solution import Solution


@streamable
class Body:
    coinbase_signature: BLSSignature
    coinbase_coin: Coin
    fees_coin: Coin
    solution_program: hash_pointer(Solution, std_hash)
    program_cost: uint64
    aggregated_signature: BLSSignature
