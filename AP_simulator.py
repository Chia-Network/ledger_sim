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
from chiasim.wallet.ap_wallet import APWallet


async def proxy_for_unix_connection(path):
    reader, writer = await asyncio.open_unix_connection(path)
    return request_response_proxy(reader, writer, ledger_sim.REMOTE_SIGNATURES)

async def  update_wallets(remote, r, wallets, a_pubkey, APpuzzlehash):
    body = r.get("body")
    additions = list(additions_for_body(body))
    removals = removals_for_body(body)
    removals = [Coin.from_bin(await remote.hash_preimage(hash=x)) for x in removals]
    for wallet in wallets:
        wallet.notify(additions, removals)
        if type(wallet) is APWallet:
            wallet.ap_notify(additions, a_pubkey)
            wallet.ac_notify(additions, APpuzzlehash)

async def client_test(path):

    remote = await proxy_for_unix_connection(path)

    #Establish wallets
    wallets = [Wallet() for _ in range(3)]
    apwallet_a = APWallet()
    apwallet_b = APWallet()
    wallets.append(apwallet_a)
    wallets.append(apwallet_b)
    a_pubkey = apwallet_a.get_next_public_key().serialize()
    b_pubkey = apwallet_b.get_next_public_key().serialize()
    APpuzzlehash = apwallet_a.ap_get_new_puzzlehash(a_pubkey, b_pubkey)

    #Give our APWallet A some money
    wallet = random.choice(wallets)
    coinbase_puzzle_hash = apwallet_a.get_new_puzzlehash()
    fees_puzzle_hash = apwallet_a.get_new_puzzlehash()
    r = await remote.next_block(coinbase_puzzle_hash=coinbase_puzzle_hash,
                                fees_puzzle_hash=fees_puzzle_hash)

    #Show the current balances of wallets
    await update_wallets(remote,r, wallets, a_pubkey, APpuzzlehash)
    print([[x.amount for x in wallet.my_utxos] for wallet in wallets])

    #Wallet A locks up the puzzle with information regarding B's pubkey
    APpuzzlehash = apwallet_a.ap_get_new_puzzlehash(a_pubkey, b_pubkey)
    apwallet_a.ap_make_aggregation_puzzle(APpuzzlehash)
    approved_pubkeys = [wallets[0].get_next_public_key(), wallets[1].get_next_public_key()]
    approved_puzhash_signature_pairs = apwallet_a.ap_generate_signatures(approved_pubkeys, APpuzzlehash, b_pubkey)
    amount = 50
    spend_bundle = apwallet_a.generate_signed_transaction(amount, APpuzzlehash)
    _ = await remote.push_tx(tx=spend_bundle)
    #Commit this transaction to a block
    wallet = apwallet_a
    coinbase_puzzle_hash = wallet.get_new_puzzlehash()
    fees_puzzle_hash = wallet.get_new_puzzlehash()
    r = await remote.next_block(coinbase_puzzle_hash=coinbase_puzzle_hash,
                                fees_puzzle_hash=fees_puzzle_hash)

    #Show balances
    await update_wallets(remote,r, wallets, a_pubkey, APpuzzlehash)
    print([[x.amount for x in wallet.my_utxos] for wallet in wallets])


    #Wallet A sends more money into Wallet B using the aggregation coin
    aggregation_puzzlehash = apwallet_a.ap_get_aggregation_puzzlehash(APpuzzlehash)
    amount = 80
    spend_bundle = apwallet_a.generate_signed_transaction(amount, aggregation_puzzlehash)
    _ = await remote.push_tx(tx=spend_bundle)
    #Commit this transaction to a block
    wallet = apwallet_a
    coinbase_puzzle_hash = wallet.get_new_puzzlehash()
    fees_puzzle_hash = wallet.get_new_puzzlehash()
    r = await remote.next_block(coinbase_puzzle_hash=coinbase_puzzle_hash,
                                fees_puzzle_hash=fees_puzzle_hash)

    #Show balances
    await update_wallets(remote,r, wallets, a_pubkey, APpuzzlehash)
    print([[x.amount for x in wallet.my_utxos] for wallet in wallets])


    #Wallet B tries to aggregate coins together in wallet
    spend_bundle = apwallet_b.ap_generate_signed_aggregation_transaction(a_pubkey)
    _ = await remote.push_tx(tx=spend_bundle)
    #Commit this transaction to a block
    wallet = apwallet_a
    coinbase_puzzle_hash = wallet.get_new_puzzlehash()
    fees_puzzle_hash = wallet.get_new_puzzlehash()
    r = await remote.next_block(coinbase_puzzle_hash=coinbase_puzzle_hash,
                                fees_puzzle_hash=fees_puzzle_hash)

    #Show balances
    await update_wallets(remote,r, wallets, a_pubkey, APpuzzlehash)
    print([[x.amount for x in wallet.my_utxos] for wallet in wallets])

    breakpoint()

    #Wallet B tries to spend from approved list of transactions
    #the storage of these as well as the selection processs should be improved (moved into wallet class?)
    signatures = [approved_puzhash_signature_pairs[0][1], approved_puzhash_signature_pairs[1][1], approved_puzhash_signature_pairs[2][1]]
    ap_output = [(approved_puzhash_signature_pairs[0][0], 30), (approved_puzhash_signature_pairs[1][0], 40), (approved_puzhash_signature_pairs[2][0], 60)]
    spend_bundle = apwallet_b.ap_generate_signed_transaction(ap_output, a_pubkey, signatures)
    _ = await remote.push_tx(tx=spend_bundle)
    #Commit this transaction to a block
    wallet = apwallet_a
    coinbase_puzzle_hash = wallet.get_new_puzzlehash()
    fees_puzzle_hash = wallet.get_new_puzzlehash()
    r = await remote.next_block(coinbase_puzzle_hash=coinbase_puzzle_hash,
                                fees_puzzle_hash=fees_puzzle_hash)

    #Show balances
    await update_wallets(remote,r, wallets, a_pubkey, APpuzzlehash)
    print([[x.amount for x in wallet.my_utxos] for wallet in wallets])

    #Pause before doing infinite loop
    breakpoint()

    #Normal loop
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

        await update_wallets(remote,r, wallets, a_pubkey, APpuzzlehash)
        print([[x.amount for x in wallet.my_utxos] for wallet in wallets])

        r = await remote.all_unspents()
        print("unspents = %s" % r.get("unspents"))
        for i in range(1):
            receiving_wallet = random.choice(wallets)
            puzzlehash = receiving_wallet.get_new_puzzlehash()
            sending_wallet = random.choice([w for w in wallets if w.current_balance > 0])
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
