"""
Pay to conditions

In this puzzle program, the solution is ignored. The reveal of the puzzle
returns a fixed list of conditions. This roughly corresponds to OP_SECURETHEBAG
in bitcoin.

This is a pretty useless most of the time. But some (most?) solutions
require a delegated puzzle program, so in those cases, this is just what
the doctor ordered.
"""

import clvm

from opacity import binutils


def puzzle_for_conditions(conditions):
    return clvm.to_sexp_f([binutils.assemble("#q"), conditions])
