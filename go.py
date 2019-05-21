import argparse
import asyncio
import sys

from aiter import join_aiters, map_aiter, push_aiter


async def readers_writers_server_for_port(port):
    """
    This asynchronous iterator accepts a port and yields a triple of (reader, writer, server) when a connection
    is made to the socket.
    """

    aiter = push_aiter()
    server = await asyncio.start_server(client_connected_cb=lambda r, w: aiter.push((r, w)), port=port)
    asyncio.ensure_future(server.wait_closed()).add_done_callback(lambda f: aiter.stop())
    async for r, w in aiter:
        print("CONNECTED", r, w)
        yield r, w, server


async def rws_to_event_stream(rws):
    """
    This adaptor accepts a triple of (reader, writer, server) and turns it into a generator that yields
    messages (in the form of lines) read from the reader.
    """
    reader, writer, server = rws
    while True:
        line = await reader.readline()
        # if the connection is closed, we get a line of no bytes
        if len(line) == 0:
            break
        yield line, reader, writer, server


async def run_server(port):
    """
    Run a server on the port, and process the messages from them one at a time.
    """
    rws_aiter = readers_writers_server_for_port(port)
    event_aiter = join_aiters(map_aiter(rws_to_event_stream, rws_aiter))
    async for line, reader, writer, server in event_aiter:
        writer.write(line)
        await writer.drain()
        if line.startswith(b"close"):
            writer.close()
        if line.startswith(b"stop"):
            server.close()


def main(args=sys.argv):
    parser = argparse.ArgumentParser(
        description='Launch an asyncio loop.'
    )
    parser.add_argument("-l", "--listen", type=int, help="listen port")

    args = parser.parse_args(args=args[1:])

    loop = asyncio.get_event_loop()

    tasks = set()

    if args.listen:
        tasks.add(asyncio.ensure_future(run_server(args.listen)))

    loop.run_until_complete(asyncio.wait(tasks))


if __name__ == '__main__':
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
