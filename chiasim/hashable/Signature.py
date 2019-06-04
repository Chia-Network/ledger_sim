from typing import List

from ..atoms import bytes32, streamable

from .Message import MessageHash


def eor_bytes32(a: bytes32, b: bytes32) -> bytes32:
    return bytes32([_[0] ^ _[1] for _ in zip(a, b)])


EORPublicKey = bytes32
PublicKey = EORPublicKey


@streamable
class EORSignature:

    @streamable
    class pair:
        message_hash: MessageHash
        public_key: PublicKey

    val: bytes32

    @classmethod
    def zero(cls):
        return cls(bytes32([0] * 32))

    def validate(self, hash_key_pairs: List[pair]) -> bool:
        eor_result = self.zero().val
        for _ in hash_key_pairs:
            eor_result = eor_bytes32(eor_result, _.message_hash)
            eor_result = eor_bytes32(eor_result, _.public_key)
        return eor_result == self.val

    def __add__(self, other):
        if isinstance(other, EORSignature):
            return EORSignature(eor_bytes32(self.val, other.val))


@streamable
class EORPrivateKey:
    val: bytes32

    def sign(self, message_hash: MessageHash) -> EORSignature:
        return EORSignature(eor_bytes32(self.val, message_hash))

    def public_key(self) -> EORPublicKey:
        return EORPublicKey(self.val)


Signature = EORSignature
