from ..atoms import hash_pointer, hexbytes, merkle_list, streamable, uint64

from .Hash import Hashable, std_hash
from .Body import Body
from .Coin import Coin
from .CoinInfo import CoinInfo
from .ProofOfSpace import ProofOfSpace


@streamable
class Header(Hashable):
    previous_hash: "HeaderHash"
    timestamp: uint64
    additions: merkle_list(Coin, std_hash)
    # leaves are Coin objects and contain (coin id, amount) ordered by puzzle hash, primary input
    removals: merkle_list(CoinInfo, std_hash)
    # leaves are coin id ordered same as solutions
    proof_of_space_hash: hash_pointer(ProofOfSpace, std_hash)
    body_hash: hash_pointer(Body, std_hash)
    extension_data_hash: hash_pointer(hexbytes, std_hash)


HeaderHash = hash_pointer(Header, std_hash)
Header.__annotations__["previous_hash"] = HeaderHash
