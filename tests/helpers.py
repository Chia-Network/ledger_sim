import clvm

from opacity import binutils

from chiasim.hack.keys import PUBLIC_KEYS, KEYCHAIN
from chiasim.hashable import CoinSolution, SpendBundle, std_hash
from chiasim.puzzles import p2_delegated_puzzle
from chiasim.validation.Conditions import (
    conditions_by_opcode, make_create_coin_condition
)
from chiasim.validation.consensus import (
    conditions_for_solution, hash_key_pairs_for_conditions_dict
)


def trace_eval(eval_f, args, env):
    print("%s [%s]" % (binutils.disassemble(args), binutils.disassemble(env)))
    r = clvm.eval_f(eval_f, args, env)
    print("%s [%s] => %s\n" % (
        binutils.disassemble(args), binutils.disassemble(env), binutils.disassemble(r)))
    return r


def build_conditions():
    puzzle_program_0 = p2_delegated_puzzle.puzzle_for_pk(PUBLIC_KEYS[0])
    puzzle_program_1 = p2_delegated_puzzle.puzzle_for_pk(PUBLIC_KEYS[1])

    conditions = [make_create_coin_condition(std_hash(pp.as_bin()), amount) for pp, amount in [
        (puzzle_program_0, 1000), (puzzle_program_1, 2000),
    ]]
    return conditions


def build_spend_bundle(coin, puzzle_program):
    conditions = build_conditions()

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
