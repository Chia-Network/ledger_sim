import asyncio
import math
import time
from unittest import TestCase

from chiasim.hack.keys import build_spend_bundle, public_key_bytes_for_index
from chiasim.hashable import ProgramHash
from chiasim.puzzles import p2_delegated_conditions
from chiasim.validation.Conditions import (
    make_assert_coin_consumed_condition,
    make_assert_my_coin_id_condition,
    make_assert_block_index_exceeds_condition,
    make_assert_block_age_exceeds_condition,
    make_assert_time_exceeds_condition,
)

from .test_puzzles import farm_spendable_coin, make_client_server


def int_to_bytes(x: int) -> bytes:
    return x.to_bytes((x.bit_length() + 7) // 8, 'big')


class TestConditions(TestCase):
    def test_assert_my_id(self):
        run = asyncio.get_event_loop().run_until_complete

        remote = make_client_server()

        puzzle_program = p2_delegated_conditions.puzzle_for_pk(
            public_key_bytes_for_index(8))
        puzzle_hash = ProgramHash(puzzle_program)

        coin_1 = farm_spendable_coin(remote, puzzle_hash)
        coin_2 = farm_spendable_coin(remote, puzzle_hash)
        coin_3 = farm_spendable_coin(remote, puzzle_hash)

        conditions_coin_1 = [make_assert_my_coin_id_condition(coin_1.name())]
        solution_1 = p2_delegated_conditions.solution_for_conditions(
            puzzle_program, conditions_coin_1)
        spend_bundle = build_spend_bundle(coin_1, solution_1)
        r = run(remote.push_tx(tx=spend_bundle))
        assert r["response"].startswith("accepted")

        spend_bundle = build_spend_bundle(coin_2, solution_1)
        r = run(remote.push_tx(tx=spend_bundle))
        assert r.args[0].startswith("exception: (<Err.ASSERT_MY_COIN_ID_FAILED")

        spend_bundle = build_spend_bundle(coin_3, solution_1)
        r = run(remote.push_tx(tx=spend_bundle))
        assert r.args[0].startswith("exception: (<Err.ASSERT_MY_COIN_ID_FAILED")

    def test_assert_coin_consumed(self):
        run = asyncio.get_event_loop().run_until_complete

        remote = make_client_server()

        puzzle_program = p2_delegated_conditions.puzzle_for_pk(
            public_key_bytes_for_index(8))
        puzzle_hash = ProgramHash(puzzle_program)

        coin_1 = farm_spendable_coin(remote, puzzle_hash)
        coin_2 = farm_spendable_coin(remote, puzzle_hash)

        conditions_coin_1 = [make_assert_coin_consumed_condition(coin_2.name())]
        solution_1 = p2_delegated_conditions.solution_for_conditions(
            puzzle_program, conditions_coin_1)
        spend_bundle_1 = build_spend_bundle(coin_1, solution_1)

        # try to spend coin_1 without coin_2. Should fail.
        r = run(remote.push_tx(tx=spend_bundle_1))
        assert r.args[0].startswith("exception: (<Err.ASSERT_COIN_CONSUMED_FAILED")

        # try to spend coin_1 with coin_2. Should be okay
        spend_bundle_2 = build_spend_bundle(coin_2, solution_1)
        spend_bundle = spend_bundle_1.aggregate([spend_bundle_1, spend_bundle_2])

        r = run(remote.push_tx(tx=spend_bundle))
        assert r["response"].startswith("accepted")
        spend_bundle_2 = build_spend_bundle(coin_2, solution_1)

    def test_assert_block_index_exceeds(self):
        run = asyncio.get_event_loop().run_until_complete

        remote = make_client_server()

        puzzle_program = p2_delegated_conditions.puzzle_for_pk(
            public_key_bytes_for_index(8))
        puzzle_hash = ProgramHash(puzzle_program)

        coin_1 = farm_spendable_coin(remote, puzzle_hash)
        coin_2 = farm_spendable_coin(remote, puzzle_hash)

        conditions_coin_exceeds_block_1 = [make_assert_block_index_exceeds_condition(1)]
        conditions_coin_exceeds_block_2 = [make_assert_block_index_exceeds_condition(2)]
        conditions_coin_exceeds_block_3 = [make_assert_block_index_exceeds_condition(3)]
        conditions_coin_exceeds_block_4 = [make_assert_block_index_exceeds_condition(4)]

        # try to spend coin_1 with limit set to block 3. Should fail
        solution_1 = p2_delegated_conditions.solution_for_conditions(
            puzzle_program, conditions_coin_exceeds_block_3)
        spend_bundle_1 = build_spend_bundle(coin_1, solution_1)
        r = run(remote.push_tx(tx=spend_bundle_1))
        assert r.args[0].startswith("exception: (<Err.ASSERT_BLOCK_INDEX_EXCEEDS_FAILED")

        # try to spend coin_1 with limit set to block 2. Should succeed
        solution_2 = p2_delegated_conditions.solution_for_conditions(
            puzzle_program, conditions_coin_exceeds_block_2)
        spend_bundle_2 = build_spend_bundle(coin_1, solution_2)
        r = run(remote.push_tx(tx=spend_bundle_2))
        assert r["response"].startswith("accepted")

        # advance a block
        coin_3 = farm_spendable_coin(remote, puzzle_hash)

        # try to spend coin_2 with limit set to block 4. Should fail
        solution_3 = p2_delegated_conditions.solution_for_conditions(
            puzzle_program, conditions_coin_exceeds_block_4)
        spend_bundle_3 = build_spend_bundle(coin_2, solution_3)
        r = run(remote.push_tx(tx=spend_bundle_3))
        assert r.args[0].startswith("exception: (<Err.ASSERT_BLOCK_INDEX_EXCEEDS_FAILED")

        # try to spend coin_2 with limit set to block 4. Should succeed
        solution_4 = p2_delegated_conditions.solution_for_conditions(
            puzzle_program, conditions_coin_exceeds_block_2)
        spend_bundle_4 = build_spend_bundle(coin_2, solution_4)
        r = run(remote.push_tx(tx=spend_bundle_4))
        assert r["response"].startswith("accepted")

        # try to spend coin_3 with limit set to block 1. Should succeed
        solution_5 = p2_delegated_conditions.solution_for_conditions(
            puzzle_program, conditions_coin_exceeds_block_1)
        spend_bundle_5 = build_spend_bundle(coin_3, solution_5)
        r = run(remote.push_tx(tx=spend_bundle_5))
        assert r["response"].startswith("accepted")

    def test_assert_block_age_exceeds(self):
        run = asyncio.get_event_loop().run_until_complete

        remote = make_client_server()

        puzzle_program = p2_delegated_conditions.puzzle_for_pk(
            public_key_bytes_for_index(8))
        puzzle_hash = ProgramHash(puzzle_program)

        # farm a bunch of blocks to start
        for _ in range(20):
            farm_spendable_coin(remote, puzzle_hash)

        coin_1 = farm_spendable_coin(remote, puzzle_hash)

        conditions_block_age_exceeds_1 = [make_assert_block_age_exceeds_condition(1)]

        # try to spend coin_1 with limit set to age 1. Should fail
        solution_1 = p2_delegated_conditions.solution_for_conditions(
            puzzle_program, conditions_block_age_exceeds_1)
        spend_bundle_1 = build_spend_bundle(coin_1, solution_1)
        r = run(remote.push_tx(tx=spend_bundle_1))
        assert r.args[0].startswith("exception: (<Err.ASSERT_BLOCK_AGE_EXCEEDS_FAILED")

        # farm a block and try again. Should succeed
        farm_spendable_coin(remote, puzzle_hash)

        r = run(remote.push_tx(tx=spend_bundle_1))
        assert r["response"].startswith("accepted")

    def test_assert_time_exceeds(self):
        run = asyncio.get_event_loop().run_until_complete

        remote = make_client_server()

        puzzle_program = p2_delegated_conditions.puzzle_for_pk(public_key_bytes_for_index(8))
        puzzle_hash = ProgramHash(puzzle_program)

        coin_1 = farm_spendable_coin(remote, puzzle_hash)

        now = run(remote.skip_milliseconds(ms=int_to_bytes(0)))
        min_time = now + 1000
        conditions_time_exceeds = [make_assert_time_exceeds_condition(min_time)]

        # try to spend coin_1 with limit set to age 1. Should fail
        solution_1 = p2_delegated_conditions.solution_for_conditions(puzzle_program, conditions_time_exceeds)
        spend_bundle_1 = build_spend_bundle(coin_1, solution_1)
        r = run(remote.push_tx(tx=spend_bundle_1))

        assert r.args[0].startswith("exception: (<Err.ASSERT_TIME_EXCEEDS_FAILED")

        # wait a second, should succeed
        x = run(remote.skip_milliseconds(ms=int_to_bytes(1000)))

        r = run(remote.push_tx(tx=spend_bundle_1))
        assert r["response"].startswith("accepted")
