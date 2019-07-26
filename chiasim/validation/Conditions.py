import enum

import clvm

from opacity import binutils

from .ConsensusError import ConsensusError, Err


class ConditionOpcode(bytes, enum.Enum):
    AGG_SIG = bytes([50])
    CREATE_COIN = bytes([51])
    ASSERT_COIN_CONSUMED = bytes([52])
    ASSERT_MY_COIN_ID = bytes([53])
    ASSERT_MIN_TIME = bytes([54])


def parse_sexp_to_condition(sexp):
    assert sexp.listp()
    items = sexp.as_python()
    if not isinstance(items[0], bytes):
        raise ConsensusError(Err.INVALID_CONDITION, items)
    assert isinstance(items[0], bytes)
    opcode = items[0]
    try:
        opcode = ConditionOpcode(items[0])
    except ValueError:
        pass
    return [opcode] + items[1:]


def parse_sexp_to_conditions(sexp):
    return [parse_sexp_to_condition(_) for _ in sexp.as_iter()]


def make_create_coin_condition(puzzle_hash, amount):
    return [ConditionOpcode.CREATE_COIN, puzzle_hash, amount]


def make_assert_coin_consumed_condition(coin_name):
    return [ConditionOpcode.ASSERT_COIN_CONSUMED, coin_name]


def make_assert_my_coin_id_condition(coin_name):
    return [ConditionOpcode.ASSERT_MY_COIN_ID, coin_name]


def make_assert_min_time_condition(time):
    return [ConditionOpcode.ASSERT_MIN_TIME, time]


def conditions_by_opcode(conditions):
    opcodes = sorted(set([_[0] for _ in conditions if len(_) > 0]))
    d = {}
    for _ in opcodes:
        d[_] = list()
    for _ in conditions:
        d[_[0]].append(_)
    return d


def parse_sexp_to_conditions_dict(sexp):
    return conditions_by_opcode(parse_sexp_to_conditions(sexp))


def conditions_to_sexp(conditions):
    return clvm.to_sexp_f([binutils.assemble("#q"), conditions])
