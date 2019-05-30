import binascii

from typing import Any, BinaryIO

from .hexbytes import hexbytes
from .struct_stream import struct_stream


class bytes32(hexbytes, struct_stream):

    def __new__(self, v):
        v = bytes(v)
        if not isinstance(v, bytes) or len(v) != 32:
            raise ValueError("bad bytes32 initializer %s" % v)
        return hexbytes.__new__(self, v)

    @classmethod
    def parse(cls, f: BinaryIO) -> Any:
        b = f.read(32)
        return cls(b)

    def stream(self, f):
        assert len(self) == 32
        f.write(self)

    def __str__(self):
        return binascii.hexlify(self).decode("utf8")

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, str(self))
