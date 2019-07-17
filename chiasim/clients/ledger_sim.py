import asyncio

from chiasim.hashable import Body, CoinName, Header, HeaderHash
from chiasim.remote.client import request_response_proxy


REMOTE_SIGNATURES = dict(
    get_tip=dict(genesis_hash=HeaderHash.from_bin, tip_hash=HeaderHash.from_bin),
    next_block=dict(header=Header.from_bin, body=Body.from_bin),
    all_unspents=dict(unspents=lambda u: [CoinName.from_bin(_) for _ in u]),
)


async def connect_to_ledger_sim(host="localhost", port=9868):
    reader, writer = await asyncio.open_connection(host, port)
    return request_response_proxy(reader, writer, REMOTE_SIGNATURES)
