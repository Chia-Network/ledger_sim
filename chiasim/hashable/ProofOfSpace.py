from ..atoms import streamable

from .BLSSignature import BLSPublicKey
from .Signature import PublicKey


@streamable
class ProofOfSpace:
    pool_pubkey: BLSPublicKey
    plot_pubkey: PublicKey
    # TODO: more items
    # Farmer commitment
    # Size (k)
    # Challenge hash
    # X vals
