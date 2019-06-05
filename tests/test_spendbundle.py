import binascii

import blspy
import clvm

from opacity import binutils

from chiasim.coin.consensus import conditions_for_puzzle_hash_solution, created_outputs_for_conditions
from chiasim.coin.Conditions import make_create_coin_condition, conditions_to_sexp
from chiasim.hashable import Coin, std_hash


def prv_key_for_seed(seed):
    eprv = blspy.ExtendedPrivateKey.from_seed(seed)
    return eprv.get_private_key()


def pub_key_for_seed(seed):
    eprv = blspy.ExtendedPrivateKey.from_seed(seed)
    return eprv.get_public_key()


def make_simple_puzzle_program(pub_key):
    # want to return ((aggsig pub_key SOLN) + SOLN)
    # (cons (list aggsig PUBKEY (sha256 x0)) (call (unwrap (f (a))) (r (a))))
    aggsig = 50
    STD_SCRIPT = f"(c (c (q {aggsig}) (c (q 0x%s) (c (sha256 (wrap (f (a)))) (q ())))) (e (f (a)) (r (a))))"
    puzzle_script = binutils.assemble(STD_SCRIPT % binascii.hexlify(pub_key.serialize()).decode("utf8"))
    return clvm.to_sexp_f(puzzle_script)


def solution_for_simple_puzzle(pub_key, conditions_program):
    puzzle_program = make_simple_puzzle_program(pub_key)
    return puzzle_program, conditions_program


def make_mined_coin(puzzle_hash, block_index, amount) -> Coin:
    pass


def trace_eval(eval_f, args, env):
    print("%s [%s]" % (binutils.disassemble(args), binutils.disassemble(env)))
    r = clvm.eval_f(eval_f, args, env)
    print("%s [%s] => %s\n" % (
        binutils.disassemble(args), binutils.disassemble(env), binutils.disassemble(r)))
    return r


def make_solution_to_simple_puzzle_program(puzzle_program, conditions):
    conditions_program = conditions_to_sexp(conditions)
    solution_program_solved = conditions_program.cons(clvm.to_sexp_f([[]]))
    puzzle_hash_solution_blob = clvm.to_sexp_f([puzzle_program, solution_program_solved])
    return puzzle_hash_solution_blob


def test_1():
    pub_key_0 = pub_key_for_seed(b"foo")
    pub_key_1 = pub_key_for_seed(b"bar")
    pub_key_2 = pub_key_for_seed(b"baz")

    puzzle_program_0 = make_simple_puzzle_program(pub_key_0)
    puzzle_program_1 = make_simple_puzzle_program(pub_key_1)
    puzzle_program_2 = make_simple_puzzle_program(pub_key_2)

    conditions = [make_create_coin_condition(std_hash(pp.as_bin()), amount) for pp, amount in [
        (puzzle_program_1, 1000), (puzzle_program_2, 2000),
    ]]

    puzzle_hash_solution_blob = make_solution_to_simple_puzzle_program(puzzle_program_0, conditions)

    puzzle_hash = std_hash(puzzle_program_0.as_bin())

    output_conditions_dict = conditions_for_puzzle_hash_solution(
        puzzle_hash, puzzle_hash_solution_blob, trace_eval)
    from pprint import pprint
    pprint(output_conditions_dict)
    input_coin_info_hash = bytes([0] * 32)
    additions = created_outputs_for_conditions(output_conditions_dict, input_coin_info_hash)
    print(additions)
    assert len(additions) == 2
