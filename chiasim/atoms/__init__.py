import dataclasses

from src.util.byte_types import make_sized_bytes  # noqa
from .hash_pointer import hash_pointer  # noqa
from src.util.ints import int8, uint8, int16, uint16, int32, uint32, int64, uint64  # noqa
from src.util.streamable import streamable as streamable1


def streamable(cls):
    f1 = streamable1(cls)
    f2 = dataclasses.dataclass(frozen=True)(f1)
    return f2
