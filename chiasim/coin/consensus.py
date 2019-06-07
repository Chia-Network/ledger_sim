import clvm

from opacity import binutils

from ..hashable import BLSSignature, Coin

from .Conditions import parse_sexp_to_conditions, ConditionOpcode


# STD_SCRIPT
# accepts a puzzle hash, the puzzle program, and the solution to the puzzle program
# x0 = puzzle_hash
# x1 = solution = (puzzle_program, solution_to_puzzle_program)

# run '(compile (if (equal (sha256 (wrap (first x1))) x0) (call (first x1) (rest x1)) (raise)))'
# this compiles to something slightly more complicated that what is below

STD_SCRIPT = ("(e (i (= (sha256 (wrap (f (f (r (a)))))) (f (a))) (f (f (r (a)))) (q (x))) "
              "(f (r (f (r (a))))))")

STD_SCRIPT_SEXP = binutils.assemble(STD_SCRIPT)


def conditions_for_puzzle_hash_solution(puzzle_hash, solution_blob, eval=clvm.eval_f):
    # get the standard script for a puzzle hash and feed in the solution
    args = clvm.to_sexp_f([puzzle_hash, solution_blob])
    try:
        r = eval(eval, STD_SCRIPT_SEXP, args)
        return parse_sexp_to_conditions(r)
    except Exception:
        raise


def created_outputs_for_conditions_dict(conditions_dict, input_coin_name):
    output_coins = []
    for _ in conditions_dict.get(ConditionOpcode.CREATE_COIN, []):
        # TODO: check condition very carefully
        # (ensure there are the correct number and type of parameters)
        # maybe write a type-checking framework for conditions
        # and don't just fail with asserts
        assert len(_) == 3
        opcode, puzzle_hash, amount_bin = _
        amount = clvm.casts.int_from_bytes(amount_bin)
        coin = Coin(input_coin_name, puzzle_hash, amount)
        output_coins.append(coin)
    return output_coins


def hash_key_pairs_for_conditions_dict(conditions_dict):
    pairs = []
    for _ in conditions_dict.get(ConditionOpcode.AGG_SIG, []):
        # TODO: check types
        assert len(_) == 3
        pairs.append(BLSSignature.pair(_[1:]))
    return pairs
