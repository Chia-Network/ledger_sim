from clvm import to_sexp_f
from clvm.serialize import sexp_from_stream, sexp_to_stream
from clvm.subclass_sexp import BaseSExp

from .Hash import std_hash

from ..atoms import hash_pointer


SExp = to_sexp_f(1).__class__


class Program(SExp):
    """
    A thin wrapper around s-expression data intended to be invoked with "eval".
    """
    code: BaseSExp

    def __init__(self, v):
        if isinstance(v, SExp):
            v = v.v
        super(Program, self).__init__(v)

    @classmethod
    def parse(cls, f):
        return sexp_from_stream(f, cls.to)

    def stream(self, f):
        sexp_to_stream(self, f)

    @classmethod
    def from_bytes(cls, b):
        return self.from_bin(b)

    def __bytes__(self):
        return self.as_bin()

    def __getattribute__(self, attr_name):
        if attr_name == "code":
            # breakpoint()
            # uncomment the line above to find where ".code" is used
            return self
        return object.__getattribute__(self, attr_name)


ProgramHash = hash_pointer(Program, std_hash)
