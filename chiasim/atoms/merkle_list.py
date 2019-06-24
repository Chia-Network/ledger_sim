import math

from typing import get_type_hints, BinaryIO, Type

from .bin_methods import bin_methods
from . import make_sized_bytes, uint8


bytes32 = make_sized_bytes(32)


def pad_to_power_of_2(leaves, pad):
    count = len(leaves)
    depth = math.ceil(math.log2(count))
    pad_count = (1 << depth) - count
    return depth, tuple(leaves) + tuple([pad] * pad_count)


def merkle_hash(leaves, hash_f, pad=bytes32([0] * 32)):

    if len(leaves) == 0:
        return pad, 0

    def merkle_pair(leaves, hash_f):
        count = len(leaves)
        if count == 1:
            return leaves[0]
        midpoint = count >> 1
        blob = merkle_pair(leaves[:midpoint], hash_f) + merkle_pair(
            leaves[midpoint:], hash_f)
        return hash_f(blob)

    depth, padded_items = pad_to_power_of_2(leaves, pad)
    the_hash = merkle_pair(padded_items, hash_f)
    return the_hash, depth


def merkle_list(the_type, hash_f):

    cls_name = "%sMerkleList" % the_type.__name__
    hash_type = get_type_hints(hash_f)["return"]

    def __init__(self, *args):
        la = len(args)
        if la not in (1, 2):
            raise ValueError("wrong arg count: %s", args)
        if la == 1:
            items = list(args[0])
            if any(not isinstance(_, the_type) for _ in items):
                raise ValueError("wrong type")
            self._obj = items
            hashes = [hash_f(_.as_bin()) for _ in items]
            args = merkle_hash(hashes, hash_f)
        self.id = hash_type(args[0])
        self.depth = uint8(args[1])

    @classmethod
    def parse(cls: Type[cls_name], f: BinaryIO) -> cls_name:
        id = hash_type.parse(f)
        depth = uint8.parse(f)
        return cls(id, depth)

    def stream(self, f: BinaryIO) -> None:
        self.id.stream(f)
        self.depth.stream(f)

    async def obj(self, data_source=None):
        if self._obj is None and data_source:
            blobs = await data_source.blobs_for_merkle_hash(self)
            hashes = [hash_f(_) for _ in blobs]
            mh = merkle_hash(hashes, hash_f)
            if mh == self:
                self._obj = [the_type.from_bin(_) for _ in blobs]
        return self._obj

    def __str__(self):
        return "%s: %s[%d]" % (cls_name, self.id, self.depth)

    namespace = dict(
        __init__=__init__, obj=obj, parse=parse, stream=stream, __str__=__str__)
    merkle_list_type = type(cls_name, (bin_methods,), namespace)
    return merkle_list_type
