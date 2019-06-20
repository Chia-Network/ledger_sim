from ..atoms import hash_pointer, hexbytes, streamable, uint64

from .Hash import Hashable, std_hash
from .Body import Body
from .ProofOfSpace import ProofOfSpace


@streamable
class Header(Hashable):
    previous_hash: "HeaderHash"
    timestamp: uint64
    proof_of_space_hash: hash_pointer(ProofOfSpace, std_hash)
    body_hash: hash_pointer(Body, std_hash)
    extension_data_hash: hash_pointer(hexbytes, std_hash)


HeaderHash = hash_pointer(Header, std_hash)
Header.__annotations__["previous_hash"] = HeaderHash
