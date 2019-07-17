"""
Pay to delegated conditions

In this puzzle program, the solution must be a signed list of conditions, which
is returned literally. The

This is a pretty useless most of the time. But some (most?) solutions
require a delegated puzzle program, so in those cases, this is just what
the doctor ordered.
"""


import clvm

from opacity import binutils

from chiasim.atoms import hexbytes
from chiasim.hashable import Program
from chiasim.validation.Conditions import ConditionOpcode


def puzzle_for_pk(public_key):
    aggsig = ConditionOpcode.AGG_SIG[0]
    TEMPLATE = f"(c (c (q {aggsig}) (c (q 0x%s) (c (sha256 (wrap (a))) (q ())))) (a))"
    return Program(binutils.assemble(TEMPLATE % hexbytes(public_key)))


def solution_for_conditions(puzzle_reveal, conditions):
    return Program(clvm.to_sexp_f([puzzle_reveal.code, conditions]))
