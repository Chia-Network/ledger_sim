
from .Conditions import ConditionOpcode
from .ConsensusError import ConsensusError, Err


def assert_coin_consumed(condition, coin, context):
    if coin.name() not in context["removals"]:
        raise ConsensusError(Err.ASSERT_COIN_CONSUMED_FAILED, (coin, condition))


def assert_my_coin_id(condition, coin, context):
    if coin.name() != condition[1]:
        raise ConsensusError(Err.ASSERT_MY_COIN_ID_FAILED, (coin, condition))


CONDITION_CHECKER_LOOKUP = {
    ConditionOpcode.ASSERT_COIN_CONSUMED: assert_coin_consumed,
    ConditionOpcode.ASSERT_MY_COIN_ID: assert_my_coin_id,
}
