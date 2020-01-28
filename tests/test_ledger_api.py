import asyncio
import pathlib
import tempfile

from aiter import map_aiter

from chiasim.clients import ledger_sim
from chiasim.hack.keys import (
    conditions_for_payment, puzzle_hash_for_index, spend_coin
)
from chiasim.hashable import std_hash
from chiasim.ledger import ledger_api
from chiasim.remote.api_server import api_server
from chiasim.remote.client import request_response_proxy
from chiasim.storage import RAM_DB
from chiasim.utils.log import init_logging
from chiasim.utils.server import start_unix_server_aiter
from chiasim.wallet.deltas import additions_for_body, removals_for_body


async def proxy_for_unix_connection(path):
    reader, writer = await asyncio.open_unix_connection(path)
    return request_response_proxy(reader, writer, ledger_sim.REMOTE_SIGNATURES)


def standard_conditions():
    conditions = conditions_for_payment([
        (puzzle_hash_for_index(0), 1000),
        (puzzle_hash_for_index(1), 2000),
    ])
    return conditions


async def client_test(path):

    remote = await proxy_for_unix_connection(path)

    # test preimage API failure case
    _ = await remote.hash_preimage(hash=b'0'*32)
    assert _ is None

    coinbase_puzzle_hash = puzzle_hash_for_index(1)
    fees_puzzle_hash = puzzle_hash_for_index(6)

    r = await remote.next_block(
        coinbase_puzzle_hash=coinbase_puzzle_hash, fees_puzzle_hash=fees_puzzle_hash)
    header = r.get("header")
    body = r.get("body")

    for _ in [header, body]:
        hh = std_hash(_)
        r1 = await remote.hash_preimage(hash=hh)
        assert r1 == bytes(_)

    coinbase_coin = body.coinbase_coin

    r = await remote.all_unspents()
    print("unspents = %s" % r.get("unspents"))

    # add a SpendBundle
    conditions = standard_conditions()
    spend_bundle = spend_coin(coinbase_coin, conditions, 1)

    # break the signature
    if 0:
        sig = spend_bundle.aggregated_signature.sig
        sig = sig[:-1] + bytes([0])
        spend_bundle = spend_bundle.__class__(spend_bundle.coin_solutions, sig)

    _ = await remote.push_tx(tx=spend_bundle)
    print(_)

    my_new_coins = spend_bundle.additions()

    coinbase_puzzle_hash = puzzle_hash_for_index(2)

    r = await remote.next_block(
        coinbase_puzzle_hash=coinbase_puzzle_hash, fees_puzzle_hash=fees_puzzle_hash)
    header = r.get("header")
    body = r.get("body")

    for _ in [header, body]:
        hh = std_hash(_)
        r1 = await remote.hash_preimage(hash=hh)
        assert r1 == bytes(_)

    print(header)
    print(body)
    my_new_coins_2 = tuple(additions_for_body(body))
    assert my_new_coins == my_new_coins_2[2:]

    removals = removals_for_body(body)
    assert len(removals) == 1
    expected_coin_id = 'dff920df992b0521026ef3e7d1cd1387910d90dd357a93fa1347037354b967cb'
    assert repr(removals[0]) == f'<CoinPointer: {expected_coin_id}>'

    # add a SpendBundle
    input_coin = my_new_coins[0]
    conditions = standard_conditions()
    spend_bundle = spend_coin(coin=input_coin, conditions=conditions, index=0)
    _ = await remote.push_tx(tx=spend_bundle)
    import pprint
    pprint.pprint(_)
    assert repr(_).startswith("RemoteError")

    r = await remote.next_block(
        coinbase_puzzle_hash=coinbase_puzzle_hash, fees_puzzle_hash=fees_puzzle_hash)
    header = r.get("header")
    body = r.get("body")

    print(header)
    print(body)

    for _ in [header, body]:
        hh = std_hash(_)
        r1 = await remote.hash_preimage(hash=hh)
        assert r1 == bytes(_)

    r = await remote.all_unspents()
    print("unspents = %s" % r.get("unspents"))

    r = await remote.get_tip()
    print(r)
    header_hash = r["tip_hash"]
    header = await header_hash.obj(remote)
    assert r["tip_index"] == 3
    assert r["genesis_hash"] == bytes([0] * 32)

    # a bad SpendBundle
    input_coin = my_new_coins[1]
    spend_bundle = spend_coin(input_coin, [], 2)
    _ = await remote.push_tx(tx=spend_bundle)
    expected_coin_id = "dff920df992b0521026ef3e7d1cd1387910d90dd357a93fa1347037354b967cb"
    expected_program_id = "c28bea953c8917c78ea439517857129ba11ddd040f3f5b99ef23076bd921760b"
    assert repr(_) == (
        "RemoteError('exception: (<Err.WRONG_PUZZLE_HASH: 8>, "
        "Coin(parent_coin_info=<CoinPointer: "
        f"{expected_coin_id}>,"
        f" puzzle_hash=<ProgramPointer: {expected_program_id}>, "
        "amount=2000))')")


def test_client_server():
    init_logging()

    run = asyncio.get_event_loop().run_until_complete

    path = pathlib.Path(tempfile.mkdtemp(), "port")

    server, aiter = run(start_unix_server_aiter(path))

    rws_aiter = map_aiter(lambda rw: dict(reader=rw[0], writer=rw[1], server=server), aiter)

    initial_block_hash = bytes(([0] * 31) + [1])
    ledger = ledger_api.LedgerAPI(initial_block_hash, RAM_DB())
    server_task = asyncio.ensure_future(api_server(rws_aiter, ledger))

    run(client_test(path))
    server_task.cancel()
