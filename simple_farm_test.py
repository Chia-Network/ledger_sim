import asyncio
import logging
import sys

from chiasim.hashable import Body, Header, Program, ProgramHash
from chiasim.utils.cbor_messages import send_cbor_message, reader_to_cbor_stream

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


async def run_client(host, port):

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

    reader, writer = await asyncio.open_connection(host, port)

    pool_private_key = PRIVATE_KEYS[0]
    puzzle_program = make_simple_puzzle_program(PUBLIC_KEYS[1])
    coinbase_coin, coinbase_signature = make_coinbase_coin_and_signature(
        1, puzzle_program, pool_private_key)

    fees_puzzle_program = Program(make_simple_puzzle_program(PUBLIC_KEYS[2]))

    header, body, *rest = await farm_block(coinbase_coin, coinbase_signature, fees_puzzle_program)

    coinbase_coin1 = body.coinbase_coin
    print(coinbase_coin)
    print(coinbase_coin1)

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


def main(args=sys.argv):
    LOG_FORMAT = ('%(asctime)s [%(process)d] [%(levelname)s] '
                  '%(filename)s:%(lineno)d %(message)s')

    asyncio.tasks._DEBUG = True
    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
    logging.getLogger("asyncio").setLevel(logging.INFO)

    loop = asyncio.get_event_loop()

    tasks = set()

    tasks.add(asyncio.ensure_future(run_client("localhost", 9999)))

    loop.run_until_complete(asyncio.wait(tasks))


if __name__ == "__main__":
    main()


"""
Copyright 2019 Chia Network Inc

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
