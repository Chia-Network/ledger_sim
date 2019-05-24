import dataclasses

from .base import uint64
from .Hash import Hash
from .MerkleTreeHash import MerkleTreeHash
from .Streamable import Streamable


@dataclasses.dataclass(frozen=True)
class Header(Streamable):
    previous_hash: Hash
    timestamp: uint64
    additions: MerkleTreeHash
    # leaves are Coin objects and contain (coin id, amount) ordered by puzzle hash, primary input
    removals: MerkleTreeHash
    # leaves are coin id ordered same as solutions
    proof_of_space_hash: Hash
    body_hash: Hash
    extension_data_hash: Hash
