import dataclasses

from typing import List, Type, BinaryIO

from .base import uint16
from .base import bin_methods


def make_list_type(base_type):

    type_name = "List%s" % base_type.__name__

    @classmethod
    def parse(cls: Type[type_name], f: BinaryIO) -> type_name:
        items = []
        count = uint16.parse(f)
        for _ in range(count):
            items.append(base_type.parse(f))
        return cls(items)

    def stream(self, f: BinaryIO) -> None:
        size = uint16(len(self.items))
        size.stream(f)
        for _ in self.items:
            _.stream(f)

    fields = [("items", List[base_type])]
    bases = (bin_methods,)
    namespace = dict(parse=parse, stream=stream)
    return dataclasses.make_dataclass(
        type_name, fields, bases=bases, frozen=True, namespace=namespace)
