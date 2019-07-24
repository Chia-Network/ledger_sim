import asyncio

from chiasim.hashable import Body, CoinName, Header, HeaderHash, Unspent
from chiasim.remote.client import request_response_proxy, xform_dict


REMOTE_SIGNATURES = dict(
    get_tip=xform_dict(genesis_hash=HeaderHash.from_bin, tip_hash=HeaderHash.from_bin),
    next_block=xform_dict(header=Header.from_bin, body=Body.from_bin),
    all_unspents=xform_dict(unspents=lambda u: [CoinName.from_bin(_) for _ in u]),
    unspent_for_coin_name=lambda x: Unspent.from_bin(x) if x else None,
)


async def connect_to_ledger_sim(host="localhost", port=9868):
    reader, writer = await asyncio.open_connection(host, port)
    return request_response_proxy(reader, writer, REMOTE_SIGNATURES)
