from .make_streamable import streamable
from .Signature import PublicKey


@streamable
class ProofOfSpace:
    pool_pubkey: PublicKey
    plot_pubkey: PublicKey
    # TODO: more items
    # Farmer commitment
    # Size (k)
    # Challenge hash
    # X vals
