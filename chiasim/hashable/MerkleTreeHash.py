import math

import dataclasses

from .base import int8, bytes32
from .Hash import Hash, std_hash
from .Streamable import Streamable


@dataclasses.dataclass(frozen=True)
class MerkleTreeHash(Streamable):
    depth: int8
    id: Hash


def pad_to_power_of_2(leaves, pad):
    count = len(leaves)
    depth = math.ceil(math.log2(count))
    pad_count = (1 << depth) - count
    return depth, tuple(_.hash() for _ in leaves) + tuple([pad] * pad_count)


def merkle_hash(leaves, hash_f=std_hash, pad=bytes32([0] * 32)):

    if len(leaves) == 0:
        return pad

    def merkle_pair(leaves, hash_f):
        count = len(leaves)
        if count == 1:
            return leaves[0]
        midpoint = count >> 1
        blob = merkle_pair(leaves[:midpoint], hash_f) + merkle_pair(leaves[midpoint:], hash_f)
        return hash_f(blob)

    depth, padded_items = pad_to_power_of_2(leaves, pad)
    the_hash = merkle_pair(padded_items, hash_f)
    return MerkleTreeHash(id=the_hash, depth=int8(depth))
