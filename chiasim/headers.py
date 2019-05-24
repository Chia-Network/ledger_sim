import binascii
import hashlib
import io
import math
import struct

import dataclasses

from typing import Any, Sequence, Type, TypeVar, Union, BinaryIO, cast, Tuple, List


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


Hash = bytes32


def std_hash(b) -> Hash:
    return Hash(hashlib.sha256(b).digest())


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
                breakpoint()
                raise NotImplementedError("can't stream %s: %s" % (v, _))

    def hash(self) -> Hash:
        return std_hash(self.as_bin())


def eor_bytes32(a: bytes32, b: bytes32) -> bytes32:
    return bytes32([_[0] ^ _[1] for _ in zip(a, b)])


EORPublicKey = bytes32
PublicKey = EORPublicKey


@dataclasses.dataclass(frozen=True)
class EORSignature(Streamable):
    val: bytes32

    @classmethod
    def zero(cls):
        return cls(bytes32([0] * 32))

    def validate(self, message_hash: Hash, pubkey: EORPublicKey) -> bool:
        eor_result = eor_bytes32(self.val, message_hash)
        return eor_result == pubkey

    def __add__(self, other):
        if isinstance(other, EORSignature):
            return EORSignature(eor_bytes32(self.val, other.val))


@dataclasses.dataclass(frozen=True)
class EORPrivateKey(Streamable):
    val: bytes32

    def sign(self, message_hash: bytes32) -> EORSignature:
        return EORSignature(eor_bytes32(self.val, message_hash))

    def public_key(self) -> EORPublicKey:
        return EORPublicKey(self.val)


Signature = EORSignature


@dataclasses.dataclass(frozen=True)
class MerkleTreeHash(Streamable):
    depth: int8
    id: Hash


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
class CoinInfo(Streamable):
    parent_coin_info: Hash
    puzzle_hash: Hash


@dataclasses.dataclass(frozen=True)
class Coin(Streamable):
    coin_info: Hash
    amount: uint64

    def additions(self, solution):
        # TODO: run the script and figure out what new coins are created
        return []


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


@dataclasses.dataclass(frozen=True)
class Additions(Streamable):
    coins: Tuple[Coin]


@dataclasses.dataclass(frozen=True)
class Removals(Streamable):
    coin_ids: Tuple[Hash]


HeaderSignature = Signature


@dataclasses.dataclass(frozen=True)
class Body(Streamable):
    coinbase_signature: Signature
    coinbase_coin: Coin
    fees_coin: Coin
    solution_program_hash: Hash
    program_cost: uint64
    aggregated_solution_signature: Signature

# solution program is simply a bunch of bytes


@dataclasses.dataclass(frozen=True)
class SpendBundle(Streamable):
    spends: List[Tuple[Coin, bytes]]
    aggregated_solution_signature: Signature

    def __add__(self, other):
        return SpendBundle(
            self.spends + other.spends,
            self.aggregated_solution_signature + other.aggregated_solution_signature)

    def additions(self):
        items = []
        for coin, s in self.spends:
            items += coin.additions(s)
        return items

    def removals(self):
        return tuple(_[0] for _ in self.spends)

    def fees(self) -> uint64:
        return uint64(0)


@dataclasses.dataclass(frozen=True)
class ProofOfSpace(Streamable):
    pool_pubkey: PublicKey
    plot_pubkey: PublicKey
    # TODO: more items
    # Farmer commitment
    # Size (k)
    # Challenge hash
    # X vals
