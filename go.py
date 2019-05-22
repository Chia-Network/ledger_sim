import argparse
import asyncio
import json
import logging
import struct
import sys

import cbor

from aiter import join_aiters, map_aiter

from chiasim.wallet_server import wallet_server
from chiasim.utils.server import readers_writers_server_for_port


async def reader_to_message_stream(reader):
    """
    This adaptor accepts a reader and turns it into a generator that yields
    messages (in the form of lines) read from the reader.
    """
    while True:
        line = await reader.readline()
        # if the connection is closed, we get a line of no bytes
        if len(line) == 0:
            break
        yield line


async def event_to_message_stream(event):
    """
    This adaptor accepts a dictionary with "reader" key and turns it into a generator that yields
    tuples (messages (in the form of lines) read from the reader.
    """
    template = dict(event)

    def add_template(message):
        d = dict(template)
        d.update(message=message)
        return d

    return map_aiter(add_template, reader_to_message_stream(event["reader"]))


async def reader_to_length_prefixed_blobs(reader):
    """
    Turn a reader into a generator that yields length-prefixed blobs.
    """
    while True:
        try:
            message_size_blob = await reader.readexactly(2)
        except asyncio.IncompleteReadError:
            break
        message_size, = struct.unpack(">H", message_size_blob)
        blob = await reader.readexactly(message_size)
        yield blob


def blob_to_cbor_message(blob):
    """
    This adaptor converts blobs into cbor messages.
    """
    try:
        return cbor.loads(blob)
    except ValueError:
        pass


def send_cbor_message(msg, writer):
    msg_blob = cbor.dumps(msg)
    length_blob = struct.pack(">H", len(msg_blob))
    writer.write(length_blob)
    writer.write(msg_blob)


async def run_server(port):
    """
    Run a server on the port, and process the messages from them one at a time.
    """
    event_aiter = readers_writers_server_for_port(port)
    message_aiter = join_aiters(map_aiter(event_to_message_stream, event_aiter))
    async for event in message_aiter:
        line = event["message"]
        writer = event["writer"]
        writer.write(line)
        if line.startswith(b"close"):
            writer.close()
        if line.startswith(b"stop"):
            server = event["server"]
            server.close()


async def run_client(host, port, msg):
    reader, writer = await asyncio.open_connection(host, port)
    message = json.loads(msg)
    send_cbor_message(message, writer)
    await writer.drain()
    async for _ in map_aiter(blob_to_cbor_message, reader_to_length_prefixed_blobs(reader)):
        break
    print(_)


def client_command(args):
    return run_client(args.host, args.port, args.message)


def server_command(args):
    return run_server(args.port)


def wallet_command(args):
    return wallet_server(args.port)


def main(args=sys.argv):
    parser = argparse.ArgumentParser(
        description="Launch an asyncio loop."
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="sub-command help")

    server_parser = subparsers.add_parser(name="server", help="server")
    server_parser.add_argument("port", type=int, help="port number to listen on")
    server_parser.set_defaults(func=server_command)

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
