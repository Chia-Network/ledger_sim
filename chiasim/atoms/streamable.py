import dataclasses

from typing import Type, BinaryIO, get_type_hints

from src.util.streamable import streamable as streamable1


def streamable(cls):
    f1 = streamable1(cls)
    f2 = dataclasses.dataclass(frozen=True)(f1)
    return f2
