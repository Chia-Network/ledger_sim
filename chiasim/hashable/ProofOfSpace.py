import dataclasses

from .Streamable import Streamable
from .Signature import PublicKey


@dataclasses.dataclass(frozen=True)
class ProofOfSpace(Streamable):
    pool_pubkey: PublicKey
    plot_pubkey: PublicKey
    # TODO: more items
    # Farmer commitment
    # Size (k)
    # Challenge hash
    # X vals
