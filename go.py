import argparse
import asyncio
import sys


async def echo_server(reader, writer, server):
    while True:
        line = await reader.readline()
        if len(line) == 0:
            break
        writer.write(line)
        await writer.drain()
        if line.startswith(b"close"):
            break
        if line.startswith(b"stop"):
            server.close()
    writer.close()


async def create_echo_server(loop, port):

    server = None

    client_tasks = set()

    def client_connected(reader, writer):
        print("CONNECTED", reader, writer)
        task = asyncio.ensure_future(echo_server(reader, writer, server))
        client_tasks.add(task)

    server = await asyncio.start_server(client_connected_cb=client_connected, port=port)
    await server.wait_closed()
    await asyncio.wait(client_tasks)


def main(args=sys.argv):
    parser = argparse.ArgumentParser(
        description='Launch an asyncio loop.'
    )
    parser.add_argument("-l", "--listen", type=int, help="listen port")

    args = parser.parse_args(args=args[1:])

    loop = asyncio.get_event_loop()
    tasks = set()

    if args.listen:
        tasks.add(asyncio.ensure_future(create_echo_server(loop, args.listen)))
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
