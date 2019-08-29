"""
Pay to m of n direct

This puzzle program is like p2_delegated_puzzle except instead of one public key,
it includes N public keys, any M of which needs to sign the delegated puzzle.
"""

import clvm
import pkg_resources

from clvm_tools import binutils
import stage_2

from chiasim.hashable import Program

make_puzzle_src = pkg_resources.resource_string(__name__, "make_puzzle_m_of_n_direct.clvm").decode("utf8")

make_puzzle_sexp = binutils.assemble(make_puzzle_src)

eval_f = stage_2.EVAL_F


def puzzle_for_m_of_public_key_list(m, public_key_list):
    args = clvm.to_sexp_f((make_puzzle_sexp, [m, public_key_list]))
    puzzle_prog_creator = eval_f(eval_f, stage_2.run, args)
    puzzle_prog = eval_f(eval_f, stage_2.run, (puzzle_prog_creator, []))
    return Program(puzzle_prog)


def solution_for_delegated_puzzle(m, public_key_list, selectors, puzzle, solution):
    puzzle_reveal = puzzle_for_m_of_public_key_list(m, public_key_list)
    return Program(clvm.to_sexp_f([puzzle_reveal.code, [selectors, puzzle.code, solution]]))
