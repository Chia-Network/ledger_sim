import asyncio
import pathlib
import tempfile

from aiter import map_aiter

from chiasim import wallet_api
from chiasim.api_decorators import transform_args
from chiasim.api_server import api_server
from chiasim.hashable import Body, CoinName, Header, Program, ProgramHash
from chiasim.remote.meta import make_proxy
from chiasim.storage import RAM_DB
from chiasim.utils.cbor_messages import reader_to_cbor_stream, send_cbor_message
from chiasim.utils.server import start_unix_server_aiter

from tests.helpers import build_spend_bundle, make_simple_puzzle_program, PRIVATE_KEYS, PUBLIC_KEYS
from tests.test_farmblock import fake_proof_of_space, make_coinbase_coin_and_signature


async def invoke_remote(method, remote, *args, **kwargs):
    reader, writer = remote.get("reader"), remote.get("writer")
    signatures = remote.get("signatures")
    msg = dict(c=method)
    msg.update(kwargs)
    send_cbor_message(msg, writer)
    await writer.drain()
    return await accept_response(reader, signatures.get(method))


async def accept_response(reader, transformation):
    async for _ in reader_to_cbor_stream(reader):
        break
    if transformation:
        _ = transform_args(transformation, _)
    return _


async def proxy_for_unix_connection(path):
    signatures = dict(
        farm_block=dict(header=Header.from_bin, body=Body.from_bin),
        all_unspents=dict(unspents=lambda u: [CoinName.from_bin(_) for _ in u]),
    )

    reader, writer = await asyncio.open_unix_connection(path)
    d = dict(reader=reader, writer=writer, signatures=signatures)
    return make_proxy(invoke_remote, d)


async def client_test(path):

    remote = await proxy_for_unix_connection(path)

    pos = fake_proof_of_space()
    pool_private_key = PRIVATE_KEYS[0]
    puzzle_program = make_simple_puzzle_program(PUBLIC_KEYS[1])
    coinbase_coin, coinbase_signature = make_coinbase_coin_and_signature(
        1, puzzle_program, pool_private_key)

    fees_puzzle_hash = ProgramHash(Program(make_simple_puzzle_program(PUBLIC_KEYS[2])))

    r = await remote.farm_block(
        pos=pos, coinbase_coin=coinbase_coin, coinbase_signature=coinbase_signature,
        fees_puzzle_hash=fees_puzzle_hash)
    header = r.get("header")
    body = r.get("body")

    coinbase_coin1 = body.coinbase_coin
    print(coinbase_coin)
    print(coinbase_coin1)

    r = await remote.all_unspents()
    print("unspents = %s" % r.get("unspents"))

    # add a SpendBundle
    spend_bundle = build_spend_bundle(coinbase_coin, puzzle_program)

    # break the signature
    if 0:
        sig = spend_bundle.aggregated_signature.sig
        sig = sig[:-1] + bytes([0])
        spend_bundle = spend_bundle.__class__(spend_bundle.coin_solutions, sig)

    _ = await remote.push_tx(tx=spend_bundle)
    print(_)

    my_new_coins = spend_bundle.additions()

    pool_private_key = PRIVATE_KEYS[0]
    puzzle_program = make_simple_puzzle_program(PUBLIC_KEYS[2])
    coinbase_coin, coinbase_signature = make_coinbase_coin_and_signature(
        2, puzzle_program, pool_private_key)

    r = await remote.farm_block(
        pos=pos, coinbase_coin=coinbase_coin, coinbase_signature=coinbase_signature,
        fees_puzzle_hash=fees_puzzle_hash)
    header = r.get("header")
    body = r.get("body")

    print(header)
    print(body)

    # add a SpendBundle
    pp = make_simple_puzzle_program(PUBLIC_KEYS[0])
    input_coin = my_new_coins[0]
    spend_bundle = build_spend_bundle(coin=input_coin, puzzle_program=pp, conditions=[])
    _ = await remote.push_tx(tx=spend_bundle)
    import pprint
    pprint.pprint(_)

    r = await remote.farm_block(
        pos=pos, coinbase_coin=coinbase_coin, coinbase_signature=coinbase_signature,
        fees_puzzle_hash=fees_puzzle_hash)
    header = r.get("header")
    body = r.get("body")

    print(header)
    print(body)

    r = await remote.all_unspents()
    print("unspents = %s" % r.get("unspents"))


def test_client_server():
    import logging
    LOG_FORMAT = ('%(asctime)s [%(process)d] [%(levelname)s] '
                  '%(filename)s:%(lineno)d %(message)s')

    asyncio.tasks._DEBUG = True
    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
    logging.getLogger("asyncio").setLevel(logging.INFO)

    run = asyncio.get_event_loop().run_until_complete

    path = pathlib.Path(tempfile.mkdtemp(), "port")

    server, aiter = run(start_unix_server_aiter(path))

    rws_aiter = map_aiter(lambda rw: dict(reader=rw[0], writer=rw[1], server=server), aiter)

    initial_block_hash = bytes(([0] * 31) + [1])
    wallet = wallet_api.WalletAPI(initial_block_hash, RAM_DB())
    server_task = asyncio.ensure_future(api_server(rws_aiter, wallet))

    run(client_test(path))
    server_task.cancel()