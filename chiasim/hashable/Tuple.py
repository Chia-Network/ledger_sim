import dataclasses

from typing import Type, BinaryIO

from .base import bin_methods


def make_tuple_type(*type_tuple):

    type_name = "Tuple%s" % ("".join("_%s" % _.__name__ for _ in type_tuple))

    fields = [("f%d" % _, t) for _, t in enumerate(type_tuple)]

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

    methods = dict(parse=parse, stream=stream)
    return dataclasses.make_dataclass(
        type_name, fields, bases=(bin_methods,), frozen=True, namespace=methods)
