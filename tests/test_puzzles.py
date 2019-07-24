import asyncio
import pathlib
import tempfile

from aiter import map_aiter

from chiasim.clients import ledger_sim
from chiasim.hack.keys import (
    conditions_for_payment, private_key_for_index,
    public_key_bytes_for_index, puzzle_hash_for_index
)
from chiasim.hashable import BLSSignature, Coin, CoinSolution, ProgramHash, SpendBundle
from chiasim.ledger import ledger_api
from chiasim.puzzles import (
    p2_conditions, p2_delegated_conditions, p2_delegated_puzzle
)
from chiasim.remote.api_server import api_server
from chiasim.remote.client import request_response_proxy
from chiasim.storage import RAM_DB
from chiasim.utils.log import init_logging
from chiasim.utils.server import start_unix_server_aiter
from chiasim.validation.Conditions import conditions_by_opcode
from chiasim.validation.consensus import (
    conditions_for_solution, hash_key_pairs_for_conditions_dict
)
from tests.BLSPrivateKey import BLSPrivateKey


async def proxy_for_unix_connection(path):
    reader, writer = await asyncio.open_unix_connection(path)
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
    return remote, server_task


def sign_f_for_keychain(keychain):
    def sign_f(aggsig_pair):
        bls_private_key = keychain.get(aggsig_pair.public_key)
        if bls_private_key:
            return bls_private_key.sign(aggsig_pair.message_hash)
        raise ValueError("unknown pubkey %s" % aggsig_pair.public_key)
    return sign_f


def signature_for_solution(solution, sign_f):
    signatures = []
    conditions_dict = conditions_by_opcode(conditions_for_solution(solution.code))
    for _ in hash_key_pairs_for_conditions_dict(conditions_dict):
        signature = sign_f(_)
        signatures.append(signature)
    return BLSSignature.aggregate(signatures)


def farm_spendable_coin(remote, puzzle_hash=puzzle_hash_for_index(0)):
    run = asyncio.get_event_loop().run_until_complete

    r = run(remote.next_block(
        coinbase_puzzle_hash=puzzle_hash, fees_puzzle_hash=puzzle_hash_for_index(1)))
    body = r.get("body")

    coinbase_coin = body.coinbase_coin
    return coinbase_coin


def run_test(puzzle_hash, solution, payments, sign_f=None):
    run = asyncio.get_event_loop().run_until_complete

    remote, server_task = make_client_server()

    coin = farm_spendable_coin(remote, puzzle_hash)

    # create a SpendBundle

    coin_solution = CoinSolution(coin, solution)
    signature = signature_for_solution(solution, sign_f)
    spend_bundle = SpendBundle([coin_solution], signature)

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
    assert len(unspents) == 8

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

    private_keys = [BLSPrivateKey(private_key_for_index(_)) for _ in range(10)]
    keychain = dict((_.public_key(), _) for _ in private_keys)
    run_test(puzzle_hash, solution, payments, sign_f_for_keychain(keychain))


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

    private_keys = [BLSPrivateKey(private_key_for_index(_)) for _ in range(10)]
    keychain = dict((_.public_key(), _) for _ in private_keys)
    run_test(puzzle_hash, solution, payments, sign_f_for_keychain(keychain))


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

    private_keys = [BLSPrivateKey(private_key_for_index(_)) for _ in range(10)]
    keychain = dict((_.public_key(), _) for _ in private_keys)
    run_test(puzzle_hash, solution, payments, sign_f_for_keychain(keychain))
