import binascii

from typing import Any, BinaryIO

from .hexbytes import hexbytes
from .struct_stream import struct_stream


def make_sized_bytes(size):

    name = "bytes%d" % size

    def __new__(self, v):
        v = bytes(v)
        if not isinstance(v, bytes) or len(v) != size:
            raise ValueError("bad %s initializer %s" % (name, v))
        return hexbytes.__new__(self, v)

    @classmethod
    def parse(cls, f: BinaryIO) -> Any:
        b = f.read(size)
        assert len(b) == size
        return cls(b)

    def stream(self, f):
        f.write(self)

    def __str__(self):
        return binascii.hexlify(self).decode("utf8")

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, str(self))

    namespace = dict(__new__=__new__, parse=parse, stream=stream, __str__=__str__, __repr__=__repr__)

    cls = type(name, (hexbytes, struct_stream), namespace)

    return cls


bytes32 = make_sized_bytes(32)
bytes48 = make_sized_bytes(48)
bytes96 = make_sized_bytes(96)
