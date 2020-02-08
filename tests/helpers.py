import asyncio
import pathlib
import tempfile

from aiter import map_aiter

from chiasim.clients import ledger_sim
from chiasim.ledger import ledger_api
from chiasim.remote.api_server import api_server
from chiasim.remote.client import request_response_proxy
from chiasim.storage import RAM_DB
from chiasim.utils.log import init_logging
from chiasim.utils.server import start_unix_server_aiter

DEFAULT_FEES_PUZZLE_HASH = bytes([0] * 32)


async def proxy_for_unix_connection(path):
    reader, writer = await asyncio.open_unix_connection(str(path))
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
    remote = run(proxy_for_unix_connection(str(path)))
    # make sure server_task isn't garbage collected
    remote.server_task = server_task
    return remote


def farm_spendable_coin(remote, coinbase_puzzle_hash, fees_puzzle_hash=DEFAULT_FEES_PUZZLE_HASH):
    run = asyncio.get_event_loop().run_until_complete

    r = run(
        remote.next_block(
            coinbase_puzzle_hash=coinbase_puzzle_hash, fees_puzzle_hash=fees_puzzle_hash
        )
    )
    body = r.get("body")

    coinbase_coin = body.coinbase_coin
    return coinbase_coin
