import dataclasses

from typing import Type, BinaryIO

from .base import streamable
from .Hash import Hash, std_hash


class Streamable(streamable):

    @classmethod
    def parse(cls: Type["Streamable"], f: BinaryIO) -> "Streamable":
        values = []
        for _ in cls.fields():
            v = _.type
            if hasattr(v, "parse"):
                values.append(v.parse(f))
            else:
                raise NotImplementedError
        return cls(*values)

    @classmethod
    def fields(cls):
        for field in dataclasses.fields(cls):
            yield field

    def stream(self, f: BinaryIO) -> None:
        for _ in self.fields():
            v = getattr(self, _.name)
            if hasattr(v, "stream"):
                v.stream(f)
            else:
                breakpoint()
                raise NotImplementedError("can't stream %s: %s" % (v, _))

    def hash(self) -> Hash:
        return std_hash(self.as_bin())
