import binascii

import blspy
import clvm

from opacity import binutils

from chiasim.coin.consensus import conditions_for_puzzle_hash_solution, created_outputs_for_conditions
from chiasim.coin.Conditions import conditions_by_opcode
from chiasim.hashable import BLSSignature, Coin, Puzzle, Solution, std_hash


def prv_key_for_seed(seed):
    eprv = blspy.ExtendedPrivateKey.from_seed(seed)
    return eprv.get_private_key()


def pub_key_for_seed(seed):
    eprv = blspy.ExtendedPrivateKey.from_seed(seed)
    return eprv.get_public_key()

    #coinbase_signature = BLSSignature(pool_prvkey.sign_prepend_prehashed(std_hash(coinbase_coin.as_bin())).serialize())


def make_simple_puzzle_program(pub_key):
    # want to return ((aggsig pub_key SOLN) + SOLN)
    # (cons (list aggsig PUBKEY (sha256 x0)) (unwrap x0))
    aggsig = 50
    STD_SCRIPT = f"(c (c (q {aggsig}) (c (q 0x%s) (c (sha256 (f (a))) (q ())))) (unwrap (f (a))))"
    puzzle_script = binutils.assemble(STD_SCRIPT % binascii.hexlify(pub_key.serialize()).decode("utf8"))
    return clvm.to_sexp_f(puzzle_script)


def solution_for_simple_puzzle(pub_key, conditions_program): # -> (SExp, SExp):
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


def test_1():
    pub_key = pub_key_for_seed(b"foo")

    conditions_program = binutils.assemble("(q 0xdeadbeef)")

    puzzle_program = make_simple_puzzle_program(pub_key)
    solution_program = conditions_program
    solution_program_solved = conditions_program.cons(clvm.to_sexp_f([]))
    puzzle_hash_solution_blob = clvm.to_sexp_f([puzzle_program, solution_program_solved.as_bin()])

    puzzle_hash = std_hash(puzzle_program.as_bin())

    output_conditions_dict = conditions_for_puzzle_hash_solution(puzzle_hash, puzzle_hash_solution_blob)
    from pprint import pprint
    pprint(output_conditions_dict)
    input_coin_info_hash = bytes([0] * 32)
    print(created_outputs_for_conditions(output_conditions_dict, input_coin_info_hash))
