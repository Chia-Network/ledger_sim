import argparse
import asyncio
import logging
import sys

from chiasim.utils.event_stream import rws_to_event_aiter
from chiasim.utils.log import init_logging
from chiasim.utils.readline_messages import reader_to_readline_stream
from chiasim.utils.server import readers_writers_server_for_port


async def run_server(port):
    """
    Run a server on the port, and process the messages from them one at a time.
    """
    rws_aiter = readers_writers_server_for_port(port)
    event_aiter = rws_to_event_aiter(rws_aiter, reader_to_readline_stream)
    async for event in event_aiter:
        line = event["message"]
        writer = event["writer"]
        writer.write(line)
        if line.startswith(b"close"):
            writer.close()
        if line.startswith(b"stop"):
            server = event["server"]
            server.close()


def server_command(args):
    return run_server(args.port)


def main(args=sys.argv):
    parser = argparse.ArgumentParser(
        description="Launch an asyncio loop."
    )

    parser.add_argument("port", type=int, help="port number to listen on")
    parser.set_defaults(func=server_command)

    args = parser.parse_args(args=args[1:])

    init_logging()

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
