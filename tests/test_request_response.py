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

    vals = [[_*10 for _ in range(count)] for count in range(10)]

    time = asyncio.get_event_loop().time

    now = time()
    # spin up 10 remote requests
    tasks = [asyncio.ensure_future(remote.add_numbers(vals=_, delay=500)) for _ in vals]
    totals = [await _ for _ in tasks]
    later = time()
    for total, val in zip(totals, vals):
        assert total == sum(val)
    delay = later - now
    assert delay < 0.600


class test_api:
    async def do_add_numbers(self, vals, delay, **kwargs):
        total = sum(vals)
        # tweak the delay so the responses come out of order
        delay -= total
        await asyncio.sleep(delay/1000)
        return total


def serve_api_on_unix_port(api, path):
    run = asyncio.get_event_loop().run_until_complete
    server, aiter = run(start_unix_server_aiter(path))
    rws_aiter = map_aiter(lambda rw: dict(reader=rw[0], writer=rw[1], server=server), aiter)
    return asyncio.ensure_future(api_server(rws_aiter, api, 20))


def test_client_server():
    init_logging()

    run = asyncio.get_event_loop().run_until_complete

    path = pathlib.Path(tempfile.mkdtemp(), "port")
    server_task = serve_api_on_unix_port(test_api(), path)

    run(client_test(path))
    server_task.cancel()
