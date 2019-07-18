import clvm

from opacity import binutils

from chiasim.hack.keys import KEYCHAIN, puzzle_hash, conditions_for_payment
from chiasim.hashable import CoinSolution, SpendBundle
from chiasim.puzzles import p2_delegated_puzzle
from chiasim.validation.Conditions import conditions_by_opcode
from chiasim.validation.consensus import (
    conditions_for_solution, hash_key_pairs_for_conditions_dict
)


def trace_eval(eval_f, args, env):
    print("%s [%s]" % (binutils.disassemble(args), binutils.disassemble(env)))
    r = clvm.eval_f(eval_f, args, env)
    print("%s [%s] => %s\n" % (
        binutils.disassemble(args), binutils.disassemble(env), binutils.disassemble(r)))
    return r


def build_spend_bundle(coin, puzzle_program):
    conditions = conditions_for_payment([
        (puzzle_hash(0), 1000),
        (puzzle_hash(1), 2000),
    ])

    solution = p2_delegated_puzzle.solution_for_conditions(puzzle_program, conditions)
    coin_solution = CoinSolution(coin, solution)

    signatures = []
    conditions_dict = conditions_by_opcode(conditions_for_solution(coin_solution.solution.code))
    for _ in hash_key_pairs_for_conditions_dict(conditions_dict):
        print(_)
        bls_private_key = KEYCHAIN.get(_.public_key)
        signature = bls_private_key.sign(_.message_hash)
        signatures.append(signature)

    signature = signatures[0].aggregate(signatures)
    spend_bundle = SpendBundle([coin_solution], signature)
    return spend_bundle
