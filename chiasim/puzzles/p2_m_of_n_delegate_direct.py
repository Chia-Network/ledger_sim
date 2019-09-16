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


eval_f = stage_2.EVAL_F

make_puzzle_src = pkg_resources.resource_string(__name__, "make_puzzle_m_of_n_direct.clvm").decode("utf8")

make_puzzle_sexp = binutils.assemble(make_puzzle_src)
puzzle_prog_template = eval_f(eval_f, stage_2.run, make_puzzle_sexp.to([make_puzzle_sexp]))


def puzzle_for_m_of_public_key_list(m, public_key_list):
    format_tuple = tuple(
        binutils.disassemble(clvm.to_sexp_f(_))
        for _ in (puzzle_prog_template, m, public_key_list))
    puzzle_src = "(e (q %s) (c (q %s) (c (q %s) (a))))" % format_tuple
    puzzle_prog = binutils.assemble(puzzle_src)
    return Program(puzzle_prog)


def solution_for_delegated_puzzle(m, public_key_list, selectors, puzzle, solution):
    puzzle_reveal = puzzle_for_m_of_public_key_list(m, public_key_list)
    return Program(clvm.to_sexp_f([puzzle_reveal, [selectors, puzzle, solution]]))
