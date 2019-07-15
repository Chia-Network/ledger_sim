import clvm

from opacity import binutils

from ..hashable import BLSSignature, Coin, CoinName, CoinNameData

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


def solution_program_output(body):
    sexp = clvm.eval_f(clvm.eval_f, body.solution_program.code, [])
    r = []
    for _ in sexp.as_iter():
        coin_name = CoinName(_.first().as_python())
        solution = _.rest().first()
        r.append((coin_name, solution))
    return r


async def coin_for_coin_name(coin_name, storage, unspent_db):
    coin_name_data_blob = await storage.hash_preimage(coin_name)
    if coin_name_data_blob is None:
        return None
    coin_name_data = CoinNameData.from_bin(coin_name_data_blob)
    unspent = await unspent_db.unspent_for_coin_name(CoinName(coin_name_data))
    coin = Coin(coin_name_data.parent_coin_info, coin_name_data.puzzle_hash, unspent.amount)
    return coin


def additions_for_solution(coin_name, solution):
    return created_outputs_for_conditions_dict(
        conditions_dict_for_solution(solution), coin_name)


async def additions_for_body(body, storage):
    yield body.coinbase_coin
    yield body.fees_coin
    for (coin_name, solution) in solution_program_output(body):
        for _ in additions_for_solution(coin_name, solution):
            yield _


def removals_for_body(body):
    coin_name_solution_pairs = solution_program_output(body)
    return [_[0] for _ in coin_name_solution_pairs]
