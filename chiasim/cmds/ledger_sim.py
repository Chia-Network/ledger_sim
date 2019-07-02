import argparse
import asyncio
import logging
import sys

from aiter import map_aiter

from chiasim import wallet_api
from chiasim.remote.api_server import api_server
from chiasim.storage import RAM_DB
from chiasim.utils.server import start_server_aiter


def run_wallet_api(server, aiter):
    INITIAL_BLOCK_HASH = bytes(([0] * 31) + [1])
    wallet = wallet_api.WalletAPI(INITIAL_BLOCK_HASH, RAM_DB())
    rws_aiter = map_aiter(lambda rw: dict(reader=rw[0], writer=rw[1], server=server), aiter)
    return api_server(rws_aiter, wallet)


def wallet_command(args):
    server, aiter = asyncio.get_event_loop().run_until_complete(start_server_aiter(args.port))
    return run_wallet_api(server, aiter)


def main(args=sys.argv):
    parser = argparse.ArgumentParser(
        description="Chia ledger simulator."
    )
    parser.add_argument("port", help="remote port")
    parser.set_defaults(func=wallet_command)

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