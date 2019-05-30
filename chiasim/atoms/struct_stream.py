import struct

from typing import Any, BinaryIO

from .bin_methods import bin_methods


class struct_stream(bin_methods):
    @classmethod
    def parse(cls, f: BinaryIO) -> Any:
        return cls(*struct.unpack(cls.PACK, f.read(struct.calcsize(cls.PACK))))

    def stream(self, f):
        f.write(struct.pack(self.PACK, self))
