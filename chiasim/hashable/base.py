import binascii
import io
import struct

from typing import Any, BinaryIO


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
