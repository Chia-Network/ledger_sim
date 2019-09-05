import asyncio
import pathlib
import tempfile

from aiter import map_aiter

from chiasim.clients import ledger_sim
from chiasim.hack.keys import (
    build_spend_bundle, conditions_for_payment,
    public_key_bytes_for_index, puzzle_hash_for_index
)
from chiasim.hashable import Coin, ProgramHash
from chiasim.ledger import ledger_api
from chiasim.puzzles import (
    p2_conditions, p2_delegated_conditions, p2_delegated_puzzle,
    p2_puzzle_hash, p2_m_of_n_delegate_direct
)
from chiasim.remote.api_server import api_server
from chiasim.remote.client import request_response_proxy
from chiasim.storage import RAM_DB
from chiasim.utils.log import init_logging
from chiasim.utils.server import start_unix_server_aiter


async def proxy_for_unix_connection(path):
    reader, writer = await asyncio.open_unix_connection(str(path))
    return request_response_proxy(reader, writer, ledger_sim.REMOTE_SIGNATURES)


def make_client_server():
    init_logging()
    run = asyncio.get_event_loop().run_until_complete
    path = pathlib.Path(tempfile.mkdtemp(), "port")
    server, aiter = run(start_unix_server_aiter(path))
    rws_aiter = map_aiter(lambda rw: dict(reader=rw[0], writer=rw[1], server=server), aiter)
    initial_block_hash = bytes(([0] * 31) + [1])
    ledger = ledger_api.LedgerAPI(initial_block_hash, RAM_DB())
    server_task = asyncio.ensure_future(api_server(rws_aiter, ledger))
    remote = run(proxy_for_unix_connection(path))
    # make sure server_task isn't garbage collected
    remote.server_task = server_task
    return remote


def farm_spendable_coin(remote, puzzle_hash=puzzle_hash_for_index(0)):
    run = asyncio.get_event_loop().run_until_complete

    r = run(remote.next_block(
        coinbase_puzzle_hash=puzzle_hash, fees_puzzle_hash=puzzle_hash_for_index(1)))
    body = r.get("body")

    coinbase_coin = body.coinbase_coin
    return coinbase_coin


def run_test(puzzle_hash, solution, payments):
    run = asyncio.get_event_loop().run_until_complete

    remote = make_client_server()

    coin = farm_spendable_coin(remote, puzzle_hash)
    spend_bundle = build_spend_bundle(coin, solution)

    # push it
    r = run(remote.push_tx(tx=spend_bundle))
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


def test_p2_conditions():
    payments = [
        (puzzle_hash_for_index(0), 1000),
        (puzzle_hash_for_index(1), 2000),
    ]

    conditions = conditions_for_payment(payments)

    puzzle_hash = ProgramHash(p2_conditions.puzzle_for_conditions(conditions))
    solution = p2_conditions.solution_for_conditions(conditions)

    run_test(puzzle_hash, solution, payments)


def test_p2_delegated_conditions():
    payments = [
        (puzzle_hash_for_index(0), 1000),
        (puzzle_hash_for_index(1), 2000),
    ]

    conditions = conditions_for_payment(payments)

    pk = public_key_bytes_for_index(1)

    puzzle_program = p2_delegated_conditions.puzzle_for_pk(pk)
    puzzle_hash = ProgramHash(puzzle_program)
    solution = p2_delegated_conditions.solution_for_conditions(puzzle_program, conditions)

    run_test(puzzle_hash, solution, payments)


def test_p2_delegated_puzzle_simple():
    payments = [
        (puzzle_hash_for_index(0), 1000),
        (puzzle_hash_for_index(1), 2000),
    ]

    conditions = conditions_for_payment(payments)

    pk = public_key_bytes_for_index(1)

    puzzle_program = p2_delegated_puzzle.puzzle_for_pk(pk)
    puzzle_hash = ProgramHash(puzzle_program)
    solution = p2_delegated_puzzle.solution_for_conditions(puzzle_program, conditions)

    run_test(puzzle_hash, solution, payments)


def test_p2_delegated_puzzle_graftroot():
    payments = [
        (puzzle_hash_for_index(0), 1000),
        (puzzle_hash_for_index(1), 2000),
    ]
    conditions = conditions_for_payment(payments)

    delegated_puzzle = p2_delegated_conditions.puzzle_for_pk(public_key_bytes_for_index(8))
    delegated_solution = p2_delegated_conditions.solution_for_conditions(delegated_puzzle, conditions)

    puzzle_program = p2_delegated_puzzle.puzzle_for_pk(public_key_bytes_for_index(1))
    puzzle_hash = ProgramHash(puzzle_program)
    solution = p2_delegated_puzzle.solution_for_delegated_puzzle(puzzle_program, delegated_solution)

    run_test(puzzle_hash, solution, payments)


def test_p2_puzzle_hash():
    payments = [
        (puzzle_hash_for_index(0), 1000),
        (puzzle_hash_for_index(1), 2000),
    ]
    conditions = conditions_for_payment(payments)
    underlying_puzzle = p2_delegated_conditions.puzzle_for_pk(public_key_bytes_for_index(4))
    underlying_solution = p2_delegated_conditions.solution_for_conditions(underlying_puzzle, conditions)
    underlying_puzzle_hash = ProgramHash(underlying_puzzle)

    puzzle_program = p2_puzzle_hash.puzzle_for_puzzle_hash(underlying_puzzle_hash)
    puzzle_hash = ProgramHash(puzzle_program)
    solution = p2_puzzle_hash.solution_for_puzzle_and_solution(underlying_puzzle, underlying_solution)

    run_test(puzzle_hash, solution, payments)


def test_p2_m_of_n_delegated_puzzle():
    payments = [
        (puzzle_hash_for_index(0), 1000),
        (puzzle_hash_for_index(1), 2000),
    ]

    conditions = conditions_for_payment(payments)

    pks = [public_key_bytes_for_index(_) for _ in range(1, 6)]
    M = 3

    delegated_puzzle = p2_conditions.puzzle_for_conditions(conditions)
    delegated_solution = []

    puzzle_program = p2_m_of_n_delegate_direct.puzzle_for_m_of_public_key_list(M, pks)
    selectors = [1, [], [], 1, 1]
    solution = p2_m_of_n_delegate_direct.solution_for_delegated_puzzle(
        M, pks, selectors, delegated_puzzle, delegated_solution)
    puzzle_hash = ProgramHash(puzzle_program)

    run_test(puzzle_hash, solution, payments)
