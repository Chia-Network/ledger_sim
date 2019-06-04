from ..atoms import streamable

from .BLSSignature import BLSPublicKey
from .Signature import PublicKey


@streamable
class ProofOfSpace:
    pool_public_key: BLSPublicKey
    plot_public_key: PublicKey
    # TODO: more items
    # Farmer commitment
    # Size (k)
    # Challenge hash
    # X vals
