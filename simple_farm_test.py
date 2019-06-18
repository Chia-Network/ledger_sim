import asyncio
import logging
import sys

from chiasim.hashable import Body, Coin, Header, Program
from chiasim.utils.cbor_messages import send_cbor_message, reader_to_cbor_stream

from tests.helpers import build_spend_bundle, make_simple_puzzle_program, PUBLIC_KEYS


async def run_client(host, port):

    async def send(msg):
        send_cbor_message(msg, writer)
        await writer.drain()
        async for _ in reader_to_cbor_stream(reader):
            return _

    reader, writer = await asyncio.open_connection(host, port)

    # add a SpendBundle
    spend_bundle = build_spend_bundle()

    # break the signature
    if 0:
        sig = spend_bundle.aggregated_signature.sig
        sig = sig[:-1] + bytes([0])
        spend_bundle = spend_bundle.__class__(spend_bundle.coin_solutions, sig)

    _ = await send({
        "c": "push_tx",
        "tx": spend_bundle.as_bin()
    })
    print(_)


    # add a SpendBundle
    pp = make_simple_puzzle_program(PUBLIC_KEYS[5])
    input_coin = Coin(bytes([55] * 32), Program(pp), 50000)
    spend_bundle = build_spend_bundle(coin=input_coin, puzzle_program=pp)
    _ = await send({
        "c": "push_tx",
        "tx": spend_bundle.as_bin()
    })
    print(_)

    _ = await send({
        "c": "farm_block",
    })
    for t, k in [
        (Header, "header"),
        (Body, "body"),
    ]:
        _[k] = t.from_bin(_.get(k))

    import pprint
    pprint.pprint(_)

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
