import asyncio
from chiasim.wallet.wallet import Wallet
from chiasim.clients.ledger_sim import connect_to_ledger_sim
from chiasim.wallet.deltas import additions_for_body, removals_for_body
from chiasim.hashable import Coin
from chiasim.hashable.Body import BodyList


def view_funds(wallet):
    print([x.amount for x in wallet.my_utxos])


def add_contact(wallet):
    print("Get the details required")
    wallet.add_contact()


def view_contacts(wallet):
    for name, details in wallet.contacts:
        print(name)


def make_payment(wallet, ledger_api):
    selection = ""
    amount = -1
    print("Pick a contact to send to:")
    for name, details in wallet.contacts:
        print("  " + name)
    while selection not in wallet.contacts:
        selection = input("Choice: ")
    while amount > wallet.current_balance or amount < 0 or not amount.isdigit():
        amount = input("Amount: ")
    return wallet.generate_signed_transaction(amount, wallet.contacts[selection][0](wallet.contacts[selection][1]))


async def new_block(wallet, ledger_api):
    coinbase_puzzle_hash = wallet.get_new_puzzlehash()
    fees_puzzle_hash = wallet.get_new_puzzlehash()
    r = await ledger_api.next_block(coinbase_puzzle_hash=coinbase_puzzle_hash, fees_puzzle_hash=fees_puzzle_hash)
    body = r["body"]
    breakpoint()
    most_recent_header = r['header']
    # breakpoint()
    additions = list(additions_for_body(body))
    removals = removals_for_body(body)
    removals = [Coin.from_bin(await ledger_api.hash_preimage(hash=x)) for x in removals]
    wallet.notify(additions, removals)
    return most_recent_header


async def update_ledger(wallet, ledger_api, most_recent_header):
    if most_recent_header is None:
        r = await ledger_api.get_all_blocks()
    else:
        r = await ledger_api.get_recent_blocks(most_recent_header=most_recent_header)
    update_list = BodyList.from_bin(r)
    for body in update_list:
        additions = list(additions_for_body(body))
        removals = removals_for_body(body)
        removals = [Coin.from_bin(await ledger_api.hash_preimage(hash=x)) for x in removals]
        wallet.notify(additions, removals)


async def main():
    ledger_api = await connect_to_ledger_sim("localhost", 9868)
    selection = ""
    wallet = Wallet()
    most_recent_header = None
    while selection != "q":
        print("Select a function:")
        print("1: View Funds")
        print("2: Add Contact")
        print("3: Make Payment")
        print("4: View Contacts")
        print("5: Get Update")
        print("6: *GOD MODE* Commit Block / Get Money")
        print("q: Quit")
        selection = input()
        if selection == "1":
            view_funds(wallet)
        elif selection == "2":
            add_contact(wallet)
        elif selection == "3":
            ledger_api.push_tx(tx=make_payment(wallet))
        elif selection == "4":
            view_contacts(wallet)
        elif selection == "5":
            await update_ledger(wallet, ledger_api, most_recent_header)
        elif selection == "6":
            most_recent_header = await new_block(wallet, ledger_api)


run = asyncio.get_event_loop().run_until_complete
run(main())
