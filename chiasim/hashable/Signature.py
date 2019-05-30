from ..atoms import bytes32, streamable

from .Message import MessageHash


def eor_bytes32(a: bytes32, b: bytes32) -> bytes32:
    return bytes32([_[0] ^ _[1] for _ in zip(a, b)])


EORPublicKey = bytes32
PublicKey = EORPublicKey


@streamable
class EORSignature:
    val: bytes32

    @classmethod
    def zero(cls):
        return cls(bytes32([0] * 32))

    def validate(self, message_hash: MessageHash, pubkey: EORPublicKey) -> bool:
        eor_result = eor_bytes32(self.val, message_hash)
        return eor_result == pubkey

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
