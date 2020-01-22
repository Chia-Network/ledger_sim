"""
Pay to delegated puzzle or hidden puzzle

In this puzzle program, the solution must choose either a hidden puzzle or a
delegated puzzle on a given public key.

The given public key is morphed by adding an offset from the hash of the hidden puzzle
and itself, giving a new so-called "synthetic" public key which has the hidden puzzle
hidden inside of it.

If the hidden puzzle path is taken, the hidden puzzle and original public key will be revealed
which proves that it was hidden there in the first place.

This roughly corresponds to bitcoin's taproot.
"""
import hashlib

import clvm

from clvm.casts import int_from_bytes

from clvm_tools import binutils

from chiasim.hashable import Program

from .load_clvm import load_clvm


DEFAULT_HIDDEN_PUZZLE = binutils.assemble("(x)")


puzzle_prog_template = load_clvm("make_p2_delegated_puzzle_or_hidden_puzzle.clvm")


def run(program, args):
    eval_f = clvm.eval_f
    sexp = binutils.assemble(program)
    args = clvm.to_sexp_f(args)
    r = eval_f(eval_f, sexp, args)
    return r.as_python()


def calculate_synthetic_offset(public_key, hidden_puzzle_hash):
    blob = hashlib.sha256(bytes(public_key) + hidden_puzzle_hash).digest()
    return int_from_bytes(blob)


def calculate_synthetic_public_key(public_key, hidden_puzzle):
    args = (public_key, hidden_puzzle)
    r = run(
        "(point_add (f (a)) (pubkey_for_exp (sha256 (f (a)) (sha256tree (r (a))))))",
        args,
    )
    return r


def puzzle_for_synthetic_public_key(synthetic_public_key):
    puzzle_src = f"((c (q {binutils.disassemble(puzzle_prog_template)}) (c (q 0x{synthetic_public_key.hex(),}) (a))))"
    puzzle_prog = binutils.assemble(puzzle_src)
    return Program(puzzle_prog)


def puzzle_for_public_key_and_hidden_puzzle(
    public_key, hidden_puzzle=DEFAULT_HIDDEN_PUZZLE
):
    synthetic_public_key = calculate_synthetic_public_key(public_key, hidden_puzzle)

    return puzzle_for_synthetic_public_key(synthetic_public_key)


def solution_with_delegated_puzzle(synthetic_public_key, delegated_puzzle, solution):
    puzzle = puzzle_for_synthetic_public_key(synthetic_public_key)
    return Program.to([puzzle, [[], delegated_puzzle, solution]])


def solution_with_hidden_puzzle(
    hidden_public_key, hidden_puzzle, solution_to_hidden_puzzle
):
    synthetic_public_key = calculate_synthetic_public_key(
        hidden_public_key, hidden_puzzle
    )
    puzzle = puzzle_for_synthetic_public_key(synthetic_public_key)
    return Program.to(
        [puzzle, [hidden_public_key, hidden_puzzle, solution_to_hidden_puzzle]]
    )
