import asyncio
import pathlib
import tempfile

from aiter import map_aiter

from chiasim.remote.api_server import api_server
from chiasim.remote.client import request_response_proxy
from chiasim.utils.server import start_unix_server_aiter

from tests.log import init_logging


async def proxy_for_unix_connection(path):
    reader, writer = await asyncio.open_unix_connection(path)
    return request_response_proxy(reader, writer)


async def client_test(path):

    remote = await proxy_for_unix_connection(path)

    vals = [10, 20, 30]
    total = await remote.add_numbers(vals=vals, delay=1)
    assert total == sum(vals)


class test_api:
    async def do_add_numbers(self, vals, delay, **kwargs):
        total = sum(vals)
        await asyncio.sleep(delay)
        return total


def serve_api_on_unix_port(api, path):
    run = asyncio.get_event_loop().run_until_complete
    server, aiter = run(start_unix_server_aiter(path))
    rws_aiter = map_aiter(lambda rw: dict(reader=rw[0], writer=rw[1], server=server), aiter)
    return asyncio.ensure_future(api_server(rws_aiter, api))


def test_client_server():
    init_logging()

    run = asyncio.get_event_loop().run_until_complete

    path = pathlib.Path(tempfile.mkdtemp(), "port")
    server_task = serve_api_on_unix_port(test_api(), path)

    run(client_test(path))
    server_task.cancel()
