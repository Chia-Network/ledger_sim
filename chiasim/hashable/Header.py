from .base import uint64, hexbytes
from .Hash import Hash
from .Body import Body
from .Coin import Coin
from .CoinInfo import CoinInfo
from .ProofOfSpace import ProofOfSpace
from .hash_pointer import hash_pointer
from .make_streamable import streamable
from .merkle_list import merkle_list


@streamable
class Header:
    previous_hash: Hash
    timestamp: uint64
    additions: merkle_list(Coin)
    # leaves are Coin objects and contain (coin id, amount) ordered by puzzle hash, primary input
    removals: merkle_list(CoinInfo)
    # leaves are coin id ordered same as solutions
    proof_of_space_hash: hash_pointer(ProofOfSpace)
    body_hash: hash_pointer(Body)
    extension_data_hash: hash_pointer(hexbytes)
