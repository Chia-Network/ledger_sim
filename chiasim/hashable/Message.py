import blspy

from ..atoms import streamable, hash_pointer, hexbytes, bytes32

from .Hash import std_hash


def bls_hash(s) -> bytes32:
    return blspy.Util.hash256(s)


@streamable
class Message:
    data: hexbytes

    def stream(self, f):
        f.write(self.data)


MessageHash = hash_pointer(Message, bls_hash)
