import binascii
import hashlib
import io
import math
import struct

import dataclasses

from typing import Any, Sequence, Type, TypeVar, Union, BinaryIO, cast


class hexbytes(bytes):
    def __str__(self):
        return binascii.hexlify(self).decode("utf8")

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, str(self))


class streamable:
    @classmethod
    def from_bin(cls, blob: bytes) -> Any:
        f = io.BytesIO(blob)
        return cls.parse(f)

    @classmethod
    def parse(cls, f: BinaryIO) -> Any:
        return cls(*struct.unpack(cls.PACK, f.read(struct.calcsize(cls.PACK))))

    def stream(self, f):
        f.write(struct.pack(self.PACK, self))

    def as_bin(self) -> hexbytes:
        f = io.BytesIO()
        self.stream(f)
        return hexbytes(f.getvalue())


class int8(int, streamable):
    PACK = "!b"


class uint64(int, streamable):
    PACK = "!Q"


class bytes32(hexbytes, streamable):
    @classmethod
    def parse(cls, f: BinaryIO) -> Any:
        b = f.read(32)
        assert len(b) == 32
        return cls(b)

    def stream(self, f):
        assert len(self) == 32
        f.write(self)

    def __str__(self):
        return binascii.hexlify(self).decode("utf8")

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, str(self))


def std_hash(b) -> bytes32:
    return bytes32(hashlib.sha256(b).digest())


class Streamable(streamable):

    @classmethod
    def parse(cls: Type["Streamable"], f: BinaryIO) -> "Streamable":
        values = []
        for _ in cls.fields():
            v = _.type
            if hasattr(v, "parse"):
                values.append(v.parse(f))
            else:
                raise NotImplementedError
        return cls(*values)

    @classmethod
    def fields(cls):
        for field in dataclasses.fields(cls):
            yield field

    def stream(self, f: BinaryIO) -> None:
        for _ in self.fields():
            v = getattr(self, _.name)
            if hasattr(v, "stream"):
                v.stream(f)
            else:
                raise NotImplementedError

    def hash(self) -> bytes32:
        return std_hash(self.as_bin())


class Signature(hexbytes):
    pass


@dataclasses.dataclass
class MerkleTreeHash(Streamable):
    depth: int8
    id: bytes32


def pad_to_power_of_2(leaves, pad):
    count = len(leaves)
    depth = math.ceil(math.log2(count))
    pad_count = (1 << depth) - count
    return depth, tuple(_.hash() for _ in leaves) + tuple([pad] * pad_count)


def merkle_hash(leaves, hash_f=std_hash, pad=hexbytes([0] * 32)):

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


@dataclasses.dataclass(frozen=True)
class Coin(Streamable):
    id: bytes32
    amount: uint64


@dataclasses.dataclass(frozen=True)
class Header(Streamable):
    previous_hash: bytes32
    timestamp: int
    additions: MerkleTreeHash
    # leaves are Coin objects and contain (coin id, amount) ordered by puzzle hash, primary input
    removals: MerkleTreeHash
    # leaves are coin id ordered same as solutions
    proof_of_space_hash: bytes32
    body_hash: bytes32
    extension_data_hash: bytes32
    signature: Signature
    # Signature of all previous things to plot key
