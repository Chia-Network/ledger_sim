import asyncio
import pathlib
import tempfile

from aiter import map_aiter

from chiasim import wallet_api
from chiasim.api_server import api_server
from chiasim.hashable import Body, CoinName, Header, Program, ProgramHash
from chiasim.storage import RAM_DB
from chiasim.utils.cbor_messages import send_cbor_message, reader_to_cbor_stream
from chiasim.utils.server import start_unix_server_aiter

from tests.helpers import build_spend_bundle, make_simple_puzzle_program, PRIVATE_KEYS, PUBLIC_KEYS
from tests.test_farmblock import fake_proof_of_space, make_coinbase_coin_and_signature


def transform_to_streamable(d):
    if hasattr(d, "as_bin"):
        return d.as_bin()
    if isinstance(d, (str, bytes, int)):
        return d
    if isinstance(d, dict):
        new_d = {}
        for k, v in d.items():
            new_d[transform_to_streamable(k)] = transform_to_streamable(v)
        return new_d
    return [transform_to_streamable(_) for _ in d]


async def client_test(path):

    async def send(msg):
        msg = transform_to_streamable(msg)
        send_cbor_message(msg, writer)
        await writer.drain()
        async for _ in reader_to_cbor_stream(reader):
            return _

    async def farm_block(coinbase_coin, coinbase_signature, fees_puzzle_hash, proof_of_space=None):
        if proof_of_space is None:
            proof_of_space = fake_proof_of_space()
        _ = await send({
            "c": "farm_block",
            "pos": proof_of_space,
            "coinbase_coin": coinbase_coin,
            "coinbase_signature": coinbase_signature,
            "fees_puzzle_hash": ProgramHash(fees_puzzle_hash),
        })
        r = []
        for t, k in [
            (Header, "header"),
            (Body, "body"),
        ]:
            r.append(t.from_bin(_.get(k)))
        return r

    reader, writer = await asyncio.open_unix_connection(path)

    pool_private_key = PRIVATE_KEYS[0]
    puzzle_program = make_simple_puzzle_program(PUBLIC_KEYS[1])
    coinbase_coin, coinbase_signature = make_coinbase_coin_and_signature(
        1, puzzle_program, pool_private_key)

    fees_puzzle_program = Program(make_simple_puzzle_program(PUBLIC_KEYS[2]))

    header, body, *rest = await farm_block(coinbase_coin, coinbase_signature, fees_puzzle_program)

    coinbase_coin1 = body.coinbase_coin
    print(coinbase_coin)
    print(coinbase_coin1)

    r = await send(dict(c="all_unspents"))
    unspents = [CoinName.from_bin(_) for _ in r.get("unspents")]
    print(unspents)

    # add a SpendBundle
    spend_bundle = build_spend_bundle(coinbase_coin, puzzle_program)

    # break the signature
    if 0:
        sig = spend_bundle.aggregated_signature.sig
        sig = sig[:-1] + bytes([0])
        spend_bundle = spend_bundle.__class__(spend_bundle.coin_solutions, sig)

    _ = await send({
        "c": "push_tx",
        "tx": spend_bundle
    })
    print(_)

    my_new_coins = spend_bundle.additions()

    pool_private_key = PRIVATE_KEYS[0]
    puzzle_program = make_simple_puzzle_program(PUBLIC_KEYS[2])
    coinbase_coin, coinbase_signature = make_coinbase_coin_and_signature(
        2, puzzle_program, pool_private_key)

    header, body, *rest = await farm_block(coinbase_coin, coinbase_signature, fees_puzzle_program)

    print(header)
    print(body)

    # add a SpendBundle
    pp = make_simple_puzzle_program(PUBLIC_KEYS[0])
    input_coin = my_new_coins[0]
    spend_bundle = build_spend_bundle(coin=input_coin, puzzle_program=pp, conditions=[])
    _ = await send({
        "c": "push_tx",
        "tx": spend_bundle
    })
    import pprint
    pprint.pprint(_)

    header, body, *rest = await farm_block(coinbase_coin, coinbase_signature, fees_puzzle_program)

    print(header)
    print(body)

    writer.close()


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
