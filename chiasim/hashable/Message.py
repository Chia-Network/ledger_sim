from ..atoms import streamable, hash_pointer, hexbytes

from .Hash import std_hash


@streamable
class Message:
    data: hexbytes

    def stream(self, f):
        f.write(self.data)


MessageHash = hash_pointer(Message, std_hash)
