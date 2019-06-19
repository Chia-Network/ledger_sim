import argparse
import asyncio
import json
import logging
import sys

from chiasim import wallet_api
from chiasim.api_server import api_server
from chiasim.storage import RAM_DB
from chiasim.utils.cbor_messages import send_cbor_message, reader_to_cbor_stream


async def run_client(host, port, msg):
    reader, writer = await asyncio.open_connection(host, port)
    message = json.loads(msg)
    send_cbor_message(message, writer)
    await writer.drain()
    async for _ in reader_to_cbor_stream(reader):
        break
    print(_)
    writer.close()


def client_command(args):
    return run_client(args.host, args.port, args.message)


def wallet_command(args):
    INITIAL_BLOCK_HASH = bytes(([0] * 31) + [1])
    wallet = wallet_api.WalletAPI(INITIAL_BLOCK_HASH, RAM_DB())
    return api_server(args.port, wallet)


def main(args=sys.argv):
    parser = argparse.ArgumentParser(
        description="Launch an asyncio loop."
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="sub-command help")

    client_subparser = subparsers.add_parser(name="client", help="client")
    client_subparser.add_argument("host", help="remote host")
    client_subparser.add_argument("port", help="remote port")
    client_subparser.add_argument("message", help="message")
    client_subparser.set_defaults(func=client_command)

    wallet_subparser = subparsers.add_parser(name="wallet", help="wallet server")
    wallet_subparser.add_argument("port", help="remote port")
    wallet_subparser.set_defaults(func=wallet_command)

    args = parser.parse_args(args=args[1:])

    LOG_FORMAT = ('%(asctime)s [%(process)d] [%(levelname)s] '
                  '%(filename)s:%(lineno)d %(message)s')

    asyncio.tasks._DEBUG = True
    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
    logging.getLogger("asyncio").setLevel(logging.INFO)

    loop = asyncio.get_event_loop()

    tasks = set()

    tasks.add(asyncio.ensure_future(args.func(args)))

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
