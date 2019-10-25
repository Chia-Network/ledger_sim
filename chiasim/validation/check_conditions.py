import clvm

from .Conditions import ConditionOpcode
from .ConsensusError import ConsensusError, Err


def assert_coin_consumed(condition, coin, context):
    for coin_name in condition[1:]:
        if coin_name not in context["removals"]:
            raise ConsensusError(Err.ASSERT_COIN_CONSUMED_FAILED, (coin, coin_name))


def assert_my_coin_id(condition, coin, context):
    if coin.name() != condition[1]:
        raise ConsensusError(Err.ASSERT_MY_COIN_ID_FAILED, (coin, condition))


def assert_block_index_exceeds(condition, coin, context):
    try:
        expected_block_index = clvm.casts.int_from_bytes(condition[1])
    except ValueError:
        raise ConsensusError(Err.INVALID_CONDITION, (coin, condition))
    if context["block_index"] <= expected_block_index:
        raise ConsensusError(
            Err.ASSERT_BLOCK_INDEX_EXCEEDS_FAILED, (coin, condition))


CONDITION_CHECKER_LOOKUP = {
    ConditionOpcode.ASSERT_COIN_CONSUMED: assert_coin_consumed,
    ConditionOpcode.ASSERT_MY_COIN_ID: assert_my_coin_id,
    ConditionOpcode.ASSERT_BLOCK_INDEX_EXCEEDS: assert_block_index_exceeds,
}
