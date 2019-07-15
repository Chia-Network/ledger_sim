import binascii

import blspy
import clvm

from opacity import binutils

from chiasim.hashable import Coin, CoinSolution, Program, SpendBundle, std_hash
from chiasim.validation.Conditions import (
    ConditionOpcode, conditions_by_opcode, conditions_to_sexp,
    make_create_coin_condition
)
from chiasim.validation.consensus import (
    conditions_for_solution, hash_key_pairs_for_conditions_dict
)

from .BLSPrivateKey import BLSPrivateKey


HIERARCHICAL_PRIVATE_KEY = blspy.ExtendedPrivateKey.from_seed(b"foo")
PRIVATE_KEYS = [HIERARCHICAL_PRIVATE_KEY.private_child(_).get_private_key() for _ in range(10)]
PUBLIC_KEYS = [_.get_public_key().serialize() for _ in PRIVATE_KEYS]
KEYCHAIN = {_.get_public_key().serialize(): BLSPrivateKey(_) for _ in PRIVATE_KEYS}


def make_simple_puzzle_program(pub_key):
    # want to return ((aggsig pub_key SOLN) + SOLN)
    # (cons (list aggsig PUBKEY (sha256 x0)) (call (unwrap (f (a))) (r (a))))
    aggsig = ConditionOpcode.AGG_SIG[0]
    STD_SCRIPT = f"(c (c (q {aggsig}) (c (q 0x%s) (c (sha256 (wrap (f (a)))) (q ())))) (e (f (a)) (r (a))))"
    puzzle_script = binutils.assemble(STD_SCRIPT % binascii.hexlify(pub_key).decode("utf8"))
    return clvm.to_sexp_f(puzzle_script)


def trace_eval(eval_f, args, env):
    print("%s [%s]" % (binutils.disassemble(args), binutils.disassemble(env)))
    r = clvm.eval_f(eval_f, args, env)
    print("%s [%s] => %s\n" % (
        binutils.disassemble(args), binutils.disassemble(env), binutils.disassemble(r)))
    return r


def make_solution_to_simple_puzzle_program(puzzle_program, conditions):
    conditions_program = conditions_to_sexp(conditions)
    solution_program_solved = conditions_program.cons(clvm.to_sexp_f([[]]))
    puzzle_hash_solution = clvm.to_sexp_f([puzzle_program, solution_program_solved])
    return puzzle_hash_solution


def build_conditions():
    puzzle_program_0 = make_simple_puzzle_program(PUBLIC_KEYS[0])
    puzzle_program_1 = make_simple_puzzle_program(PUBLIC_KEYS[1])

    conditions = [make_create_coin_condition(std_hash(pp.as_bin()), amount) for pp, amount in [
        (puzzle_program_0, 1000), (puzzle_program_1, 2000),
    ]]
    return conditions


def build_spend_bundle(coin=None, puzzle_program=None, conditions=None):
    if coin is None:
        puzzle_program = make_simple_puzzle_program(PUBLIC_KEYS[0])
        parent = bytes(([0] * 31) + [1])
        coin = Coin(parent, std_hash(puzzle_program.as_bin()), 50000)

    if conditions is None:
        conditions = build_conditions()

    solution = Program(make_solution_to_simple_puzzle_program(puzzle_program, conditions))
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
