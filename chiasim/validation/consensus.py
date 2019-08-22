import clvm

from opacity import binutils

from ..hashable import BLSSignature, Coin

from .Conditions import conditions_by_opcode, parse_sexp_to_conditions, ConditionOpcode


UNVERIFIED_STD_SCRIPT = "(e (f (a)) (f (r (a))))"

UNVERIFIED_STD_SCRIPT = binutils.assemble(UNVERIFIED_STD_SCRIPT)


def conditions_for_solution(solution_program, eval=clvm.eval_f):
    # get the standard script for a puzzle hash and feed in the solution
    args = clvm.to_sexp_f(solution_program)
    try:
        r = eval(eval, UNVERIFIED_STD_SCRIPT, args)
        return parse_sexp_to_conditions(r)
    except clvm.EvalError.EvalError:
        raise


def conditions_dict_for_solution(solution):
    return conditions_by_opcode(conditions_for_solution(solution))


def hash_key_pairs_for_solution(solution):
    return hash_key_pairs_for_conditions_dict(conditions_dict_for_solution(solution))


def validate_spend_bundle_signature(spend_bundle) -> bool:
    hash_key_pairs = []
    for coin_solution in spend_bundle.coin_solutions:
        hash_key_pairs += hash_key_pairs_for_solution(coin_solution.solution.code)
    return spend_bundle.aggregated_signature.validate(hash_key_pairs)


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
        pairs.append(BLSSignature.aggsig_pair(*_[1:]))
    return pairs
