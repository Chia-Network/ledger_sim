import asyncio
from unittest import TestCase

from chiasim.hack.keys import (
    build_spend_bundle, conditions_for_payment, public_key_bytes_for_index, puzzle_hash_for_index
)
from chiasim.hashable import ProgramHash, Coin
from chiasim.puzzles import (
    p2_delegated_conditions
)
from chiasim.remote.client import RemoteError
from chiasim.validation.Conditions import make_assert_my_coin_id_condition
from .test_puzzles import farm_spendable_coin, make_client_server


def run_test(puzzle_hash, payments, solution_maker):
    run = asyncio.get_event_loop().run_until_complete

    remote = make_client_server()

    coin = farm_spendable_coin(remote, puzzle_hash)
    solution = solution_maker(coin, remote)
    spend_bundle = build_spend_bundle(coin, solution)

    # push it
    r = run(remote.push_tx(tx=spend_bundle))
    if isinstance(r, RemoteError):
        raise r
    assert r["response"].startswith("accepted")
    print(r)

    # confirm it
    farm_spendable_coin(remote)

    # get unspents
    r = run(remote.all_unspents())
    print("unspents = %s" % r.get("unspents"))
    unspents = r["unspents"]

    # ensure all outputs are there
    for puzzle_hash, amount in payments:
        expected_coin = Coin(coin.name(), puzzle_hash, amount)
        name = expected_coin.name()
        assert name in unspents
        unspent = run(remote.unspent_for_coin_name(coin_name=name))
        assert unspent.confirmed_block_index == 2
        assert unspent.spent_block_index == 0


class TestStandard(TestCase):
    def test_pay_to_pubkey(self):
        payments = [
            (puzzle_hash_for_index(0), 1000),
            (puzzle_hash_for_index(1), 2000),
        ]

        conditions = conditions_for_payment(payments)

        pk = public_key_bytes_for_index(1)

        puzzle_program = p2_delegated_conditions.puzzle_for_pk(pk)
        puzzle_hash = ProgramHash(puzzle_program)

        def solution_maker(coin, _remote):
            id_condition = make_assert_my_coin_id_condition(coin.name())
            return p2_delegated_conditions.solution_for_conditions(puzzle_program,
                                                                   conditions + [id_condition])

        run_test(puzzle_hash, payments, solution_maker)

    def test_pay_to_pubkey_wrong_coin(self):
        payments = [
            (puzzle_hash_for_index(0), 1000),
            (puzzle_hash_for_index(1), 2000),
        ]

        conditions = conditions_for_payment(payments)

        pk = public_key_bytes_for_index(1)

        puzzle_program = p2_delegated_conditions.puzzle_for_pk(pk)
        puzzle_hash = ProgramHash(puzzle_program)

        def solution_maker(_coin, remote):
            coin1 = farm_spendable_coin(remote, puzzle_hash)

            id_condition = make_assert_my_coin_id_condition(coin1.name())
            return p2_delegated_conditions.solution_for_conditions(puzzle_program,
                                                                   conditions + [id_condition])

        try:
            run_test(puzzle_hash, payments, solution_maker)
        except RemoteError as ex:
            self.assertTrue(ex.args[0].startswith("exception: (<Err.ASSERT_MY_COIN_ID_FAILED"))
