from clvm import to_sexp_f
from clvm.more_ops import sha256tree
from clvm.serialize import sexp_from_stream, sexp_to_stream
from clvm.subclass_sexp import BaseSExp

from .sized_bytes import bytes32
from ..atoms import bin_methods


SExp = to_sexp_f(1).__class__


class Program(SExp, bin_methods):
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

    def tree_hash(self):
        return sha256tree(self)

    def __str__(self):
        return bytes(self).hex()


class ProgramPointer(bytes32):

    the_hash: bytes32

    def __new__(cls, v):
        if isinstance(v, SExp):
            v = Program(v).tree_hash()
        return bytes32.__new__(cls, v)


# we actually want the revealed name to be ProgramPointer for some reason
ProgramHash = ProgramPointer
