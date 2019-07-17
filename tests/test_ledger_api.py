import asyncio
import pathlib
import tempfile

from aiter import map_aiter

from chiasim.clients import ledger_sim
from chiasim.ledger import ledger_api
from chiasim.hashable import Program, ProgramHash
from chiasim.puzzles import p2_delegated_puzzle
from chiasim.remote.api_server import api_server
from chiasim.remote.client import request_response_proxy
from chiasim.storage import RAM_DB
from chiasim.utils.log import init_logging
from chiasim.utils.server import start_unix_server_aiter
from chiasim.wallet.deltas import additions_for_body, removals_for_body

from tests.helpers import build_spend_bundle, PUBLIC_KEYS


async def proxy_for_unix_connection(path):
    reader, writer = await asyncio.open_unix_connection(path)
    return request_response_proxy(reader, writer, ledger_sim.REMOTE_SIGNATURES)


async def client_test(path):

    remote = await proxy_for_unix_connection(path)

    puzzle_sexp = p2_delegated_puzzle.puzzle_for_pk(PUBLIC_KEYS[1])
    coinbase_puzzle_hash = ProgramHash(Program(puzzle_sexp))
    fees_puzzle_hash = ProgramHash(Program(p2_delegated_puzzle.puzzle_for_pk(PUBLIC_KEYS[6])))

    r = await remote.next_block(
        coinbase_puzzle_hash=coinbase_puzzle_hash, fees_puzzle_hash=fees_puzzle_hash)
    header = r.get("header")
    body = r.get("body")

    coinbase_coin = body.coinbase_coin

    r = await remote.all_unspents()
    print("unspents = %s" % r.get("unspents"))

    # add a SpendBundle
    spend_bundle = build_spend_bundle(coinbase_coin, puzzle_sexp)

    # break the signature
    if 0:
        sig = spend_bundle.aggregated_signature.sig
        sig = sig[:-1] + bytes([0])
        spend_bundle = spend_bundle.__class__(spend_bundle.coin_solutions, sig)

    _ = await remote.push_tx(tx=spend_bundle)
    print(_)

    my_new_coins = spend_bundle.additions()

    coinbase_puzzle_hash = ProgramHash(Program(p2_delegated_puzzle.puzzle_for_pk(PUBLIC_KEYS[2])))

    r = await remote.next_block(
        coinbase_puzzle_hash=coinbase_puzzle_hash, fees_puzzle_hash=fees_puzzle_hash)
    header = r.get("header")
    body = r.get("body")

    print(header)
    print(body)
    my_new_coins_2 = tuple(additions_for_body(body))
    assert my_new_coins == my_new_coins_2[2:]

    removals = removals_for_body(body)
    assert len(removals) == 1
    assert repr(removals[0]) == '<CoinNameDataPointer: 1bf5bbf69b15b052b5b14d39f3a5c4c4e51525172c57f4f05ab184990ea9ab0b>'

    # add a SpendBundle
    pp = p2_delegated_puzzle.puzzle_for_pk(PUBLIC_KEYS[0])
    input_coin = my_new_coins[0]
    spend_bundle = build_spend_bundle(coin=input_coin, puzzle_program=pp, conditions=[])
    _ = await remote.push_tx(tx=spend_bundle)
    import pprint
    pprint.pprint(_)

    r = await remote.next_block(
        coinbase_puzzle_hash=coinbase_puzzle_hash, fees_puzzle_hash=fees_puzzle_hash)
    header = r.get("header")
    body = r.get("body")

    print(header)
    print(body)

    r = await remote.all_unspents()
    print("unspents = %s" % r.get("unspents"))

    r = await remote.get_tip()
    print(r)
    header_hash = r["tip_hash"]
    header = await header_hash.obj(remote)
    assert r["tip_index"] == 3
    assert r["genesis_hash"] == bytes([0] * 32)


def test_client_server():
    init_logging()

    run = asyncio.get_event_loop().run_until_complete

    path = pathlib.Path(tempfile.mkdtemp(), "port")

    server, aiter = run(start_unix_server_aiter(path))

    rws_aiter = map_aiter(lambda rw: dict(reader=rw[0], writer=rw[1], server=server), aiter)

    initial_block_hash = bytes(([0] * 31) + [1])
    ledger = ledger_api.LedgerAPI(initial_block_hash, 1, RAM_DB())
    server_task = asyncio.ensure_future(api_server(rws_aiter, ledger))

    run(client_test(path))
    server_task.cancel()
