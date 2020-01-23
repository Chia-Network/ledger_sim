import asyncio
import pathlib
import tempfile
from unittest import TestCase

from aiter import map_aiter

from chiasim.hack.keys import build_spend_bundle, public_key_bytes_for_index, puzzle_hash_for_index
from chiasim.hashable import ProgramHash
from chiasim.hack import p2_delegated_conditions
from chiasim.validation.Conditions import (
    make_assert_coin_consumed_condition,
    make_assert_my_coin_id_condition,
    make_assert_block_index_exceeds_condition,
    make_assert_block_age_exceeds_condition,
)
from chiasim.clients import ledger_sim
from chiasim.remote.api_server import api_server
from chiasim.remote.client import request_response_proxy
from chiasim.ledger import ledger_api
from chiasim.storage import RAM_DB
from chiasim.utils.log import init_logging
from chiasim.utils.server import start_unix_server_aiter


async def proxy_for_unix_connection(path):
    reader, writer = await asyncio.open_unix_connection(path)
    return request_response_proxy(reader, writer, ledger_sim.REMOTE_SIGNATURES)


def make_client_server():
    init_logging()
    run = asyncio.get_event_loop().run_until_complete
    path = pathlib.Path(tempfile.mkdtemp(), "port")
    server, aiter = run(start_unix_server_aiter(path))
    rws_aiter = map_aiter(
        lambda rw: dict(reader=rw[0], writer=rw[1], server=server), aiter
    )
    initial_block_hash = bytes(([0] * 31) + [1])
    ledger = ledger_api.LedgerAPI(initial_block_hash, RAM_DB())
    server_task = asyncio.ensure_future(api_server(rws_aiter, ledger))
    remote = run(proxy_for_unix_connection(path))
    # make sure server_task isn't garbage collected
    remote.server_task = server_task
    return remote


def farm_spendable_coin(remote, puzzle_hash=puzzle_hash_for_index(0)):
    run = asyncio.get_event_loop().run_until_complete

    r = run(
        remote.next_block(
            coinbase_puzzle_hash=puzzle_hash, fees_puzzle_hash=puzzle_hash_for_index(1)
        )
    )
    body = r.get("body")

    coinbase_coin = body.coinbase_coin
    return coinbase_coin


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
