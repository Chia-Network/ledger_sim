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

from clvm_tools import binutils

from chiasim.hashable import Program
from chiasim.validation.Conditions import ConditionOpcode

from . import p2_conditions


def puzzle_for_pk(public_key):
    aggsig = ConditionOpcode.AGG_SIG[0]
    TEMPLATE = (f"(c (c (q {aggsig}) (c (q 0x%s) (c (sha256tree (f (a))) (q ())))) "
                f"((c (f (a)) (f (r (a))))))")
    return Program.to(binutils.assemble(TEMPLATE % public_key.hex()))


def solution_for_conditions(puzzle_reveal, conditions):
    delegated_puzzle = p2_conditions.puzzle_for_conditions(conditions)
    solution = []
    return Program.to([puzzle_reveal, [delegated_puzzle, solution]])


def solution_for_delegated_puzzle(puzzle_reveal, delegated_solution):
    return Program.to([puzzle_reveal, delegated_solution])
