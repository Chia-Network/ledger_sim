import asyncio
import pathlib
import tempfile

from aiter import map_aiter

from chiasim.clients import ledger_sim
from chiasim.hack.keys import (
    build_spend_bundle,
    conditions_for_payment,
    puzzle_hash_for_index,
)
from chiasim.hashable import (
    ProgramHash,
    std_hash,
)
from chiasim.ledger import ledger_api
from .p2_conditions import puzzle_for_conditions, solution_for_conditions
from chiasim.remote.api_server import api_server
from chiasim.remote.client import request_response_proxy
from chiasim.storage import RAM_DB
from chiasim.utils.log import init_logging
from chiasim.utils.server import start_unix_server_aiter


async def proxy_for_unix_connection(path):
    reader, writer = await asyncio.open_unix_connection(path)
    return request_response_proxy(reader, writer, ledger_sim.REMOTE_SIGNATURES)


def standard_conditions():
    conditions = conditions_for_payment(
        [(puzzle_hash_for_index(0), 1000), (puzzle_hash_for_index(1), 2000)]
    )
    return conditions


async def client_test(path):

    remote = await proxy_for_unix_connection(path)

    payments = [
        (puzzle_hash_for_index(0), 1000),
        (puzzle_hash_for_index(1), 2000),
    ]

    conditions = conditions_for_payment(payments)
    coinbase_puzzle_hash = ProgramHash(puzzle_for_conditions(conditions))

    fees_puzzle_hash = puzzle_hash_for_index(6)

    r = await remote.next_block(
        coinbase_puzzle_hash=coinbase_puzzle_hash, fees_puzzle_hash=fees_puzzle_hash
    )
    header = r.get("header")
    body = r.get("body")

    for _ in [header, body]:
        hh = std_hash(_)
        r1 = await remote.hash_preimage(hash=hh)
        assert r1 == bytes(_)

    coinbase_coin = body.coinbase_coin

    new_coinbase_puzzle_hash = puzzle_hash_for_index(5)

    # farm a few blocks
    for _ in range(5):
        r = await remote.next_block(
            coinbase_puzzle_hash=new_coinbase_puzzle_hash,
            fees_puzzle_hash=fees_puzzle_hash,
        )

        assert "header" in r

    # spend the coinbase coin

    solution = solution_for_conditions(conditions)
    spend_bundle = build_spend_bundle(coinbase_coin, solution)

    r = await remote.push_tx(tx=spend_bundle)
    assert r["response"].startswith("accepted")

    # farm a few blocks
    for _ in range(5):
        r = await remote.next_block(
            coinbase_puzzle_hash=new_coinbase_puzzle_hash,
            fees_puzzle_hash=fees_puzzle_hash,
        )

        assert "header" in r

    r = await remote.push_tx(tx=spend_bundle)
    assert r.args[0].startswith("exception: (<Err.DOUBLE_SPEND")

    r = await remote.all_unspents()
    coin_names = r["unspents"]
    coin_name = coin_names[0]
    assert coin_name == coinbase_coin.name()

    unspent = await remote.unspent_for_coin_name(coin_name=coin_name)
    assert unspent.spent_block_index == 7


def test_double_spend():
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

    run(client_test(path))
    server_task.cancel()
