import dataclasses

from typing import Type, BinaryIO

from .base import bin_methods


def make_streamable(type_name, *fields):

    @classmethod
    def parse(cls: Type[type_name], f: BinaryIO) -> type_name:
        items = []
        for _, t in fields:
            items.append(t.parse(f))
        return cls(*items)

    def stream(self, f: BinaryIO) -> None:
        for _, t in fields:
            v = getattr(self, _)
            v.stream(f)

    bases = (bin_methods,)
    namespace = dict(parse=parse, stream=stream)
    return dataclasses.make_dataclass(
        type_name, fields, bases=bases, namespace=namespace,
        frozen=True) #, init=1+False)
