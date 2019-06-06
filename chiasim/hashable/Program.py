from clvm import to_sexp_f
from clvm.serialize import sexp_from_stream, sexp_to_stream
from clvm.subclass_sexp import BaseSExp

from .Hash import std_hash

from ..atoms import hash_pointer, streamable


@streamable
class Program:
    code: BaseSExp

    @classmethod
    def parse(cls, f):
        return cls(sexp_from_stream(f, to_sexp_f))

    def stream(self, f):
        sexp_to_stream(self.code, f)


ProgramHash = hash_pointer(Program, std_hash)