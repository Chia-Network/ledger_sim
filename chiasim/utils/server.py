import asyncio
import logging

from aiter import push_aiter


async def readers_writers_server_for_port(port):
    """
    This asynchronous iterator accepts a port and yields a dictionary with
    keys "reader", "writer", "server" when a connection is made to the socket.
    """

    aiter = push_aiter()
    server = await asyncio.start_server(client_connected_cb=lambda r, w: aiter.push((r, w)), port=port)
    asyncio.ensure_future(server.wait_closed()).add_done_callback(lambda f: aiter.stop())
    async for r, w in aiter:
        logging.info("connection from %s", r)
        yield dict(reader=r, writer=w, server=server)


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
