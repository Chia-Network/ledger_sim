import argparse
import asyncio
import json
import logging
import sys

from chiasim.utils.cbor_messages import send_cbor_message, reader_to_cbor_stream


async def run_client(host, port, msg):
    reader, writer = await asyncio.open_connection(host, port)
    message = json.loads(msg)
    send_cbor_message(message, writer)
    await writer.drain()
    async for _ in reader_to_cbor_stream(reader):
        break
    writer.close()
    return _


def client_command(args):
    return run_client(args.host, args.port, args.message)


def main(args=sys.argv):
    parser = argparse.ArgumentParser(
        description="Chia client."
    )

    parser.add_argument("host", help="remote host")
    parser.add_argument("port", help="remote port")
    parser.add_argument("message", help="message")
    parser.set_defaults(func=client_command)

    args = parser.parse_args(args=args[1:])

    LOG_FORMAT = ('%(asctime)s [%(process)d] [%(levelname)s] '
                  '%(filename)s:%(lineno)d %(message)s')

    asyncio.tasks._DEBUG = True
    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
    logging.getLogger("asyncio").setLevel(logging.INFO)

    loop = asyncio.get_event_loop()
    r = loop.run_until_complete(args.func(args))
    print(r)


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
