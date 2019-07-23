"""
Pay to delegated puzzle

In this puzzle program, the solution must be a signed delegated puzzle, along with
its (unsigned) solution. The delegated puzzle is executed, passing in the solution.
This obviously could be done recursively, arbitrarily deep (as long as the maximum
cost is not exceeded).

If you want to specify the conditions directly (thus terminating the potential recursion),
you can use p2_conditions.

This roughly corresponds to bitcoin's graftroot.
"""

import clvm

from opacity import binutils

from chiasim.atoms import hexbytes
from chiasim.hashable import Program
from chiasim.validation.Conditions import ConditionOpcode

from . import p2_conditions


def puzzle_for_pk(public_key):
    aggsig = ConditionOpcode.AGG_SIG[0]
    TEMPLATE = (f"(c (c (q {aggsig}) (c (q 0x%s) (c (sha256 (wrap (f (a)))) (q ())))) "
                f"(e (f (a)) (f (r (a)))))")
    return Program(binutils.assemble(TEMPLATE % hexbytes(public_key)))


def solution_for_conditions(puzzle_reveal, conditions):
    delegated_puzzle = p2_conditions.puzzle_for_conditions(conditions)
    solution = []
    return Program(clvm.to_sexp_f([puzzle_reveal.code, [delegated_puzzle.code, solution]]))


def solution_for_delegated_puzzle(puzzle_reveal, delegated_puzzle, solution):
    return Program(clvm.to_sexp_f([puzzle_reveal.code, [delegated_puzzle.code, solution.code]]))