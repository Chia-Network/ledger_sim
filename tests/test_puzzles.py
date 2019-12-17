import asyncio
import pathlib
import tempfile
from unittest import TestCase

from aiter import map_aiter

from chiasim.clients import ledger_sim
from chiasim.hack.keys import (
    bls_private_key_for_index,
    build_spend_bundle,
    conditions_for_payment,
    public_key_bytes_for_index,
    puzzle_hash_for_index,
    DEFAULT_KEYCHAIN,
)
from chiasim.hashable import Coin, ProgramHash
from chiasim.ledger import ledger_api
from chiasim.puzzles import (
    p2_conditions,
    p2_delegated_conditions,
    p2_delegated_puzzle,
    p2_puzzle_hash,
    p2_m_of_n_delegate_direct,
    p2_delegated_puzzle_or_hidden_puzzle,
)
from chiasim.remote.api_server import api_server
from chiasim.remote.client import request_response_proxy
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


def default_payments_and_conditions(initial_index=1):
    payments = [
        (puzzle_hash_for_index(initial_index + 1), initial_index * 1000),
        (puzzle_hash_for_index(initial_index + 2), (initial_index + 1) * 1000),
    ]

    conditions = conditions_for_payment(payments)
    return payments, conditions


class TestPuzzles(TestCase):
    def test_p2_conditions(self):
        payments, conditions = default_payments_and_conditions()

        puzzle_hash = ProgramHash(p2_conditions.puzzle_for_conditions(conditions))
        solution = p2_conditions.solution_for_conditions(conditions)

        run_test(puzzle_hash, solution, payments)

    def test_p2_delegated_conditions(self):
        payments, conditions = default_payments_and_conditions()

        pk = public_key_bytes_for_index(1)

        puzzle_program = p2_delegated_conditions.puzzle_for_pk(pk)
        puzzle_hash = ProgramHash(puzzle_program)
        solution = p2_delegated_conditions.solution_for_conditions(
            puzzle_program, conditions
        )

        run_test(puzzle_hash, solution, payments)

    def test_p2_delegated_puzzle_simple(self):
        payments, conditions = default_payments_and_conditions()

        pk = public_key_bytes_for_index(1)

        puzzle_program = p2_delegated_puzzle.puzzle_for_pk(pk)
        puzzle_hash = ProgramHash(puzzle_program)
        solution = p2_delegated_puzzle.solution_for_conditions(
            puzzle_program, conditions
        )

        run_test(puzzle_hash, solution, payments)

    def test_p2_delegated_puzzle_graftroot(self):
        payments, conditions = default_payments_and_conditions()

        delegated_puzzle = p2_delegated_conditions.puzzle_for_pk(
            public_key_bytes_for_index(8)
        )
        delegated_solution = p2_delegated_conditions.solution_for_conditions(
            delegated_puzzle, conditions
        )

        puzzle_program = p2_delegated_puzzle.puzzle_for_pk(
            public_key_bytes_for_index(1)
        )
        puzzle_hash = ProgramHash(puzzle_program)
        solution = p2_delegated_puzzle.solution_for_delegated_puzzle(
            puzzle_program, delegated_solution
        )

        run_test(puzzle_hash, solution, payments)

    def test_p2_puzzle_hash(self):
        payments, conditions = default_payments_and_conditions()

        underlying_puzzle = p2_delegated_conditions.puzzle_for_pk(
            public_key_bytes_for_index(4)
        )
        underlying_solution = p2_delegated_conditions.solution_for_conditions(
            underlying_puzzle, conditions
        )
        underlying_puzzle_hash = ProgramHash(underlying_puzzle)

        puzzle_program = p2_puzzle_hash.puzzle_for_puzzle_hash(underlying_puzzle_hash)
        puzzle_hash = ProgramHash(puzzle_program)
        solution = p2_puzzle_hash.solution_for_puzzle_and_solution(
            underlying_puzzle, underlying_solution
        )

        run_test(puzzle_hash, solution, payments)

    def test_p2_m_of_n_delegated_puzzle(self):
        payments, conditions = default_payments_and_conditions()

        pks = [public_key_bytes_for_index(_) for _ in range(1, 6)]
        M = 3

        delegated_puzzle = p2_conditions.puzzle_for_conditions(conditions)
        delegated_solution = []

        puzzle_program = p2_m_of_n_delegate_direct.puzzle_for_m_of_public_key_list(
            M, pks
        )
        selectors = [1, [], [], 1, 1]
        solution = p2_m_of_n_delegate_direct.solution_for_delegated_puzzle(
            M, pks, selectors, delegated_puzzle, delegated_solution
        )
        puzzle_hash = ProgramHash(puzzle_program)

        run_test(puzzle_hash, solution, payments)

    def test_p2_delegated_puzzle_or_hidden_puzzle_with_hidden_puzzle(self):
        payments, conditions = default_payments_and_conditions()

        hidden_puzzle = p2_conditions.puzzle_for_conditions(conditions)
        hidden_public_key = public_key_bytes_for_index(10)

        puzzle = p2_delegated_puzzle_or_hidden_puzzle.puzzle_for_public_key_and_hidden_puzzle(
            hidden_public_key, hidden_puzzle
        )
        puzzle_hash = ProgramHash(puzzle)

        solution = p2_delegated_puzzle_or_hidden_puzzle.solution_with_hidden_puzzle(
            hidden_public_key, hidden_puzzle, []
        )

        run_test(puzzle_hash, solution, payments)

    def run_test_p2_delegated_puzzle_or_hidden_puzzle_with_delegated_puzzle(self, hidden_pub_key_index):
        payments, conditions = default_payments_and_conditions()

        hidden_puzzle = p2_conditions.puzzle_for_conditions(conditions)
        hidden_public_key = public_key_bytes_for_index(hidden_pub_key_index)

        puzzle = p2_delegated_puzzle_or_hidden_puzzle.puzzle_for_public_key_and_hidden_puzzle(
            hidden_public_key, hidden_puzzle
        )
        puzzle_hash = ProgramHash(puzzle)

        payable_payments, payable_conditions = default_payments_and_conditions(5)

        delegated_puzzle = p2_conditions.puzzle_for_conditions(payable_conditions)
        delegated_solution = []

        synthetic_public_key = p2_delegated_puzzle_or_hidden_puzzle.calculate_synthetic_public_key(
            hidden_public_key, hidden_puzzle
        )

        solution = p2_delegated_puzzle_or_hidden_puzzle.solution_with_delegated_puzzle(
            synthetic_public_key, delegated_puzzle, delegated_solution
        )

        hidden_puzzle_hash = ProgramHash(hidden_puzzle)
        synthetic_offset = p2_delegated_puzzle_or_hidden_puzzle.calculate_synthetic_offset(
            hidden_public_key, hidden_puzzle_hash
        )
        private_key = bls_private_key_for_index(hidden_pub_key_index)
        assert private_key.public_key() == hidden_public_key
        secret_exponent = private_key.secret_exponent()
        synthetic_secret_exponent = secret_exponent + synthetic_offset
        DEFAULT_KEYCHAIN.add_secret_exponents([synthetic_secret_exponent])

        run_test(puzzle_hash, solution, payable_payments)

    def test_p2_delegated_puzzle_or_hidden_puzzle_with_delegated_puzzle(self):
        for hidden_pub_key_index in range(1, 10):
            self.run_test_p2_delegated_puzzle_or_hidden_puzzle_with_delegated_puzzle(hidden_pub_key_index)
