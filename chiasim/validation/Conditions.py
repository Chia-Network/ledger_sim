import enum

import clvm

from opacity import binutils


class ConditionOpcode(bytes, enum.Enum):
    AGG_SIG = bytes([50])
    CREATE_COIN = bytes([51])


def parse_sexp_to_condition(sexp):
    assert sexp.listp()
    items = sexp.as_python()
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
