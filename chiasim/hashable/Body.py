import dataclasses

from .base import uint64
from .Coin import Coin
from .Hash import Hash
from .Signature import Signature
from .Streamable import Streamable


@dataclasses.dataclass(frozen=True)
class Body(Streamable):
    coinbase_signature: Signature
    coinbase_coin: Coin
    fees_coin: Coin
    solution_program_hash: Hash
    program_cost: uint64
    aggregated_solution_signature: Signature

# solution program is simply a bunch of bytes
