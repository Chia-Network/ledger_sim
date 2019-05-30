import binascii
import io
import struct

from typing import Any, BinaryIO


class hexbytes(bytes):
    def __str__(self):
        return binascii.hexlify(self).decode("utf8")

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, str(self))


class bin_methods:
    @classmethod
    def from_bin(cls, blob: bytes) -> Any:
        f = io.BytesIO(blob)
        return cls.parse(f)

    def as_bin(self) -> hexbytes:
        f = io.BytesIO()
        self.stream(f)
        return hexbytes(f.getvalue())


class streamable(bin_methods):
    @classmethod
    def parse(cls, f: BinaryIO) -> Any:
        return cls(*struct.unpack(cls.PACK, f.read(struct.calcsize(cls.PACK))))

    def stream(self, f):
        f.write(struct.pack(self.PACK, self))


class int8(int, streamable):
    PACK = "!b"


class uint8(int, streamable):
    PACK = "!B"


class int16(int, streamable):
    PACK = "!h"


class uint16(int, streamable):
    PACK = "!H"


class uint64(int, streamable):
    PACK = "!Q"


class bytes32(hexbytes, streamable):

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
