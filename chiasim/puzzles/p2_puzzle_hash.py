"""
Pay to puzzle hash

In this puzzle program, the solution must be a reveal of the puzzle with the given
hash along with its solution.
"""

import clvm

from opacity import binutils

from chiasim.atoms import hexbytes
from chiasim.hashable import Program, ProgramHash


"""
solution: (puzzle_reveal . solution_to_puzzle)

(if (= (sha256 (wrap puzzle_reveal)) puzzle_hash) (e puzzle_reveal solution_to_puzzle) (x))

(e (i (= (sha256 (wrap puzzle_reveal)) puzzle_hash) (q (e (f (a)) (r (a)))) (q (x)) (a))

(e (i (= (sha256 (wrap (f (a)))) CONST) (q (e (f (a)) (r (a)))) (q (x))) (a))
"""


def puzzle_for_puzzle_hash(underlying_puzzle_hash):
    TEMPLATE = "(e (i (= (sha256 (wrap (f (a)))) (q 0x%s)) (q (e (f (a)) (f (r (a))))) (q (x))) (a))"
    return Program(binutils.assemble(TEMPLATE % hexbytes(
        underlying_puzzle_hash)))


def solution_for_puzzle_and_solution(underlying_puzzle, underlying_solution):
    underlying_puzzle_hash = ProgramHash(underlying_puzzle)
    puzzle_program = puzzle_for_puzzle_hash(underlying_puzzle_hash)
    return Program(clvm.to_sexp_f([puzzle_program.code, underlying_solution.code]))
