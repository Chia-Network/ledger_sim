import asyncio
import pathlib
import tempfile
import random
import math
from aiter import map_aiter
from chiasim.clients import ledger_sim
from chiasim.ledger import ledger_api
from chiasim.hashable import Coin
from chiasim.remote.api_server import api_server
from chiasim.remote.client import request_response_proxy
from chiasim.storage import RAM_DB
from chiasim.utils.log import init_logging
from chiasim.utils.server import start_unix_server_aiter
from chiasim.wallet.deltas import additions_for_body, removals_for_body
from chiasim.wallet.wallet import Wallet


async def proxy_for_unix_connection(path):
    reader, writer = await asyncio.open_unix_connection(path)
    return request_response_proxy(reader, writer, ledger_sim.REMOTE_SIGNATURES)


async def client_test(path):

    remote = await proxy_for_unix_connection(path)

    wallets = [Wallet() for _ in range(3)]
    wallets[0].add_contact("Bob", wallets[1].export_puzzle_generator(), 0, None)
    wallets[0].add_contact("Charlie", wallets[2].export_puzzle_generator(), 0, None)
    wallets[1].add_contact("Alice", wallets[0].export_puzzle_generator(), 0, None)
    wallets[1].add_contact("Charlie", wallets[2].export_puzzle_generator(), 0, None)
    wallets[2].add_contact("Alice", wallets[0].export_puzzle_generator(), 0, None)
    wallets[2].add_contact("Bob", wallets[1].export_puzzle_generator(), 0, None)

    while True:
        wallet = random.choice(wallets)
        coinbase_puzzle_hash = wallet.get_new_puzzlehash()
        fees_puzzle_hash = wallet.get_new_puzzlehash()
        r = await remote.next_block(coinbase_puzzle_hash=coinbase_puzzle_hash,
                                    fees_puzzle_hash=fees_puzzle_hash)
        body = r.get("body")

        additions = list(additions_for_body(body))
        removals = removals_for_body(body)
        removals = [Coin.from_bin(await remote.hash_preimage(hash=x)) for x in removals]

        for wallet in wallets:
            wallet.notify(additions, removals)
        print([[x.amount for x in wallet.my_utxos] for wallet in wallets])

        r = await remote.all_unspents()
        print("unspents = %s" % r.get("unspents"))

        for i in range(1):
            sending_wallet = random.choice([w for w in wallets if w.current_balance > 0])
            receiving_contact = random.choice(sending_wallet.get_contact_names())
            puzzlehash = sending_wallet.get_puzzlehash_for_contact(receiving_contact)

            amount = math.floor(0.50 * random.random() * (sending_wallet.current_balance - 1)) + 1
            spend_bundle = sending_wallet.generate_signed_transaction(amount, puzzlehash)
            _ = await remote.push_tx(tx=spend_bundle)


def test_client_server():
    init_logging()

    run = asyncio.get_event_loop().run_until_complete

    path = pathlib.Path(tempfile.mkdtemp(), "port")

    server, aiter = run(start_unix_server_aiter(path))

    rws_aiter = map_aiter(lambda rw: dict(reader=rw[0], writer=rw[1], server=server), aiter)

    initial_block_hash = bytes(([0] * 31) + [1])
    ledger = ledger_api.LedgerAPI(initial_block_hash, RAM_DB())
    server_task = asyncio.ensure_future(api_server(rws_aiter, ledger))

    run(client_test(path))
    server_task.cancel()


test_client_server()
