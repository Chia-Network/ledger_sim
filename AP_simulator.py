import asyncio
import pathlib
import tempfile
import random
import math
from chiasim.wallet import ap_wallet_a_functions
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
from chiasim.wallet.ap_wallet import APWallet


async def proxy_for_unix_connection(path):
    reader, writer = await asyncio.open_unix_connection(path)
    return request_response_proxy(reader, writer, ledger_sim.REMOTE_SIGNATURES)


async def update_wallets(remote, r, wallets):
    body = r.get("body")
    additions = list(additions_for_body(body))
    removals = removals_for_body(body)
    removals = [Coin.from_bin(await remote.hash_preimage(hash=x)) for x in removals]
    for wallet in wallets:
        wallet.notify(additions, removals)
        if type(wallet) is APWallet:
            wallet.ap_notify(additions)
            spend_bundle_list = wallet.ac_notify(additions)
            if spend_bundle_list is not None:
                for spend_bundle in spend_bundle_list:
                    _ = await remote.push_tx(tx=spend_bundle)


async def client_test(path):

    remote = await proxy_for_unix_connection(path)

    # Establish wallets
    wallets = [Wallet() for _ in range(3)]
    apwallet_a = Wallet()
    apwallet_b = APWallet()
    wallets.append(apwallet_a)
    wallets.append(apwallet_b)
    a_pubkey = apwallet_a.get_next_public_key().serialize()
    b_pubkey = apwallet_b.get_next_public_key().serialize()
    APpuzzlehash = ap_wallet_a_functions.ap_get_new_puzzlehash(a_pubkey, b_pubkey)
    apwallet_b.set_sender_values(APpuzzlehash, a_pubkey)
    apwallet_b.set_approved_change_signature(ap_wallet_a_functions.ap_sign_output_newpuzzlehash(
        APpuzzlehash, apwallet_a, a_pubkey))

    # Give our APWallet A some money
    wallet = wallets[random.randrange(0, 3)]
    coinbase_puzzle_hash = apwallet_a.get_new_puzzlehash()
    fees_puzzle_hash = apwallet_a.get_new_puzzlehash()
    r = await remote.next_block(coinbase_puzzle_hash=coinbase_puzzle_hash,
                                fees_puzzle_hash=fees_puzzle_hash)

    # Show the current balances of wallets
    await update_wallets(remote, r, wallets)
    print([[x.amount for x in wallet.my_utxos] for wallet in wallets])

    # Wallet B adds contacts of the approved payees
    approved_puzhashes = [
        wallets[0].get_new_puzzlehash(), wallets[1].get_new_puzzlehash()]
    amount = 50

    # Wallet A locks up the puzzle with information regarding B's pubkey
    spend_bundle = apwallet_a.generate_signed_transaction(amount, APpuzzlehash)
    _ = await remote.push_tx(tx=spend_bundle)
    # Commit this transaction to a block
    wallet = wallets[2]
    coinbase_puzzle_hash = wallet.get_new_puzzlehash()
    fees_puzzle_hash = wallet.get_new_puzzlehash()
    r = await remote.next_block(coinbase_puzzle_hash=coinbase_puzzle_hash,
                                fees_puzzle_hash=fees_puzzle_hash)

    # Show balances
    await update_wallets(remote, r, wallets)
    print([[x.amount for x in wallet.my_utxos] for wallet in wallets])

    # Wallet A sends more money into Wallet B using the aggregation coin
    aggregation_puzzlehash = ap_wallet_a_functions.ap_get_aggregation_puzzlehash(
        APpuzzlehash)
    # amount = 80
    spend_bundle = apwallet_a.generate_signed_transaction(
        50, aggregation_puzzlehash)
    _ = await remote.push_tx(tx=spend_bundle)
    spend_bundle = wallets[2].generate_signed_transaction(
        30, aggregation_puzzlehash)
    _ = await remote.push_tx(tx=spend_bundle)

    # Commit this transaction to a block
    wallet = wallets[random.randrange(0, 3)]
    coinbase_puzzle_hash = wallet.get_new_puzzlehash()
    fees_puzzle_hash = wallet.get_new_puzzlehash()
    r = await remote.next_block(coinbase_puzzle_hash=coinbase_puzzle_hash,
                                fees_puzzle_hash=fees_puzzle_hash)

    # Show balances and detect new coin, and buffer auto aggregation
    await update_wallets(remote, r, wallets)
    print([[x.amount for x in wallet.my_utxos] for wallet in wallets])

    # Confirm the auto aggregate of the two coins
    wallet = wallets[random.randrange(0, 3)]
    coinbase_puzzle_hash = wallet.get_new_puzzlehash()
    fees_puzzle_hash = wallet.get_new_puzzlehash()
    r = await remote.next_block(coinbase_puzzle_hash=coinbase_puzzle_hash,
                                fees_puzzle_hash=fees_puzzle_hash)

    # Show balances
    await update_wallets(remote, r, wallets)
    print([[x.amount for x in wallet.my_utxos] for wallet in wallets])

    breakpoint()

    # Wallet B tries to spend from approved list of contacts
    #
    signatures = [ap_wallet_a_functions.ap_sign_output_newpuzzlehash(
        approved_puzhashes[0], apwallet_a, a_pubkey),
                  ap_wallet_a_functions.ap_sign_output_newpuzzlehash(
                      approved_puzhashes[1], apwallet_a, a_pubkey)]
    ap_output = [(approved_puzhashes[0], 69), (approved_puzhashes[1], 22)]
    spend_bundle = apwallet_b.ap_generate_signed_transaction(
        ap_output, signatures)
    _ = await remote.push_tx(tx=spend_bundle)
    # Commit this transaction to a block
    wallet = wallets[random.randrange(0, 3)]
    coinbase_puzzle_hash = wallet.get_new_puzzlehash()
    fees_puzzle_hash = wallet.get_new_puzzlehash()
    r = await remote.next_block(coinbase_puzzle_hash=coinbase_puzzle_hash,
                                fees_puzzle_hash=fees_puzzle_hash)

    # Show balances
    await update_wallets(remote, r, wallets)
    print([[x.amount for x in wallet.my_utxos] for wallet in wallets])

    # Pause before doing infinite loop
    breakpoint()

    # Normal loop
    while True:
        wallet = wallets[random.randrange(2)]
        coinbase_puzzle_hash = wallet.get_new_puzzlehash()
        fees_puzzle_hash = wallet.get_new_puzzlehash()
        r = await remote.next_block(coinbase_puzzle_hash=coinbase_puzzle_hash,
                                    fees_puzzle_hash=fees_puzzle_hash)
        await update_wallets(remote, r, wallets)
        print([[x.amount for x in wallet.my_utxos] for wallet in wallets])

        r = await remote.all_unspents()
        print("unspents = %s" % r.get("unspents"))
        for i in range(1):
            receiving_wallet = wallets[random.randrange(4)]
            puzzlehash = receiving_wallet.get_new_puzzlehash()
            complete = False
            while complete is False:
                sending_wallet = wallets[random.randrange(4)]
                if sending_wallet.current_balance > 0:
                    complete = True
            amount = math.floor(0.50 * random.random() *
                                (sending_wallet.current_balance - 1)) + 1
            spend_bundle = sending_wallet.generate_signed_transaction(
                amount, puzzlehash)
            _ = await remote.push_tx(tx=spend_bundle)


def test_client_server():
    init_logging()

    run = asyncio.get_event_loop().run_until_complete

    path = pathlib.Path(tempfile.mkdtemp(), "port")

    server, aiter = run(start_unix_server_aiter(path))

    rws_aiter = map_aiter(lambda rw: dict(
        reader=rw[0], writer=rw[1], server=server), aiter)

    initial_block_hash = bytes(([0] * 31) + [1])
    ledger = ledger_api.LedgerAPI(initial_block_hash, RAM_DB())
    server_task = asyncio.ensure_future(api_server(rws_aiter, ledger))

    run(client_test(path))
    server_task.cancel()


test_client_server()
