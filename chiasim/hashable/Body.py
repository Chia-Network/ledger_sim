
from ..atoms import streamable, uint64

from .BLSSignature import BLSSignature
from .Coin import Coin
from .Program import Program


@streamable
class Body:
    coinbase_signature: BLSSignature
    coinbase_coin: Coin
    fees_coin: Coin
    solution_program: Program
    program_cost: uint64
    aggregated_signature: BLSSignature
