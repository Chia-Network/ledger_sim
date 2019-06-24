import clvm

from opacity import binutils

from ..hashable import BLSSignature, Coin, CoinName, CoinNameData

from .Conditions import conditions_by_opcode, parse_sexp_to_conditions, ConditionOpcode


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


def conditions_dict_for_coin_solution(coin, solution):
    return conditions_by_opcode(conditions_for_puzzle_hash_solution(
        coin.puzzle_hash, solution))


def hash_key_pairs_for_conditions_dict(conditions_dict):
    pairs = []
    for _ in conditions_dict.get(ConditionOpcode.AGG_SIG, []):
        # TODO: check types
        assert len(_) == 3
        pairs.append(BLSSignature.aggsig_pair(*_[1:]))
    return pairs


def hash_key_pairs_for_coin_solution(coin, solution):
    return hash_key_pairs_for_conditions_dict(
        conditions_dict_for_coin_solution(coin, solution))


def solution_program_output(body):
    sexp = clvm.eval_f(clvm.eval_f, body.solution_program.code, [])
    r = []
    for _ in sexp.as_iter():
        coin_name = CoinName(_.first().as_python())
        solution = _.rest().first()
        r.append((coin_name, solution))
    return r


async def coin_for_coin_name(coin_name, storage):
    coin_name_data_blob = await storage.hash_preimage(coin_name)
    if coin_name_data_blob is None:
        return None
    coin_name_data = CoinNameData.from_bin(coin_name_data_blob)
    unspent = await storage.unspent_for_coin_name(CoinName(coin_name_data))
    coin = Coin(coin_name_data.parent_coin_info, coin_name_data.puzzle_hash, unspent.amount)
    return coin


def additions_for_coin_solution(coin, solution):
    return created_outputs_for_conditions_dict(
        conditions_dict_for_coin_solution(coin, solution), coin.coin_name())


async def additions_for_body(body, storage):
    yield body.coinbase_coin
    yield body.fees_coin
    for (coin_name, solution) in solution_program_output(body):
        coin = await coin_for_coin_name(coin_name, storage)
        for _ in additions_for_coin_solution(coin, solution):
            yield _


def removals_for_body(body):
    coin_name_solution_pairs = solution_program_output(body)
    return [_[0] for _ in coin_name_solution_pairs]
