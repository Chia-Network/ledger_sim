import asyncio
import clvm
from chiasim.wallet.wallet import Wallet
from chiasim.clients.ledger_sim import connect_to_ledger_sim
from chiasim.wallet.deltas import additions_for_body, removals_for_body
from chiasim.hashable import Coin
from chiasim.hashable.Body import BodyList
from clvm_tools import binutils
from chiasim.hashable import Program, ProgramHash
from chiasim.validation.Conditions import ConditionOpcode
from blspy import ExtendedPublicKey


def view_funds(wallet):
    print([x.amount for x in wallet.my_utxos])


def add_contact(wallet):
    name = input("What is the new contact's name? ")
    # note that we should really be swapping a function here, but thisll do
    puzzlegeneratorstring = input("What is their ChiaLisp puzzlegenerator: ")
    puzzlegenerator = binutils.assemble(puzzlegeneratorstring)
    wallet.add_contact(name, puzzlegenerator, 0, None)


def view_contacts(wallet):
    for name, details in wallet.contacts:
        print(name)


def print_my_details(wallet):
    print("Name: " + wallet.name)
    print("Puzzle Generator: ")
    print("(c (q 5) (c (c (q 5) (c (q (q 50)) (c (c (q 5) (c (c (q 1) (c (f (a)) (q ()))) (q ((c (sha256 (wrap (a))) (q ())))))) (q ())))) (q ((a)))))")
    print("New pubkey: ")
    print(wallet.get_next_public_key())
    print("Generator hash identifier:")
    print(ProgramHash(Program(binutils.assemble("(c (q 5) (c (c (q 5) (c (q (q 50)) (c (c (q 5) (c (c (q 1) (c (f (a)) (q ()))) (q ((c (sha256 (wrap (a))) (q ())))))) (q ())))) (q ((a)))))"))))

def set_name(wallet):
    selection = input("Enter a new name: ")
    wallet.set_name(selection)


def make_payment(wallet):
    selection = None
    amount = -1
    if wallet.current_balance <= 0:
        print("You need some money first")
        return None
    name = input("Name of payee:" )
    type = input("Generator hash ID: 0x")
    while amount > wallet.current_balance or amount < 0:
        amount = int(input("Amount: "))
    pubkey = input("Pubkey: 0x")
    args = binutils.assemble("(0x" + pubkey + ")")
    program = Program(clvm.eval_f(clvm.eval_f, binutils.assemble(wallet.generator_lookups[type]), args))
    puzzlehash = ProgramHash(program)
    print(puzzlehash)
    breakpoint()
    return wallet.generate_signed_transaction(amount, puzzlehash)


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
        print("7: Print my details for somebody else")
        print("8: Set my wallet name")
        print("9: Test export")
        print("q: Quit")
        selection = input()
        if selection == "1":
            view_funds(wallet)
        elif selection == "2":
            add_contact(wallet)
        elif selection == "3":
            r = make_payment(wallet)
            if r is not None:
                await ledger_api.push_tx(tx=r)
        elif selection == "4":
            view_contacts(wallet)
        elif selection == "5":
            await update_ledger(wallet, ledger_api, most_recent_header)
        elif selection == "6":
            most_recent_header = await new_block(wallet, ledger_api)
        elif selection == "7":
            print_my_details(wallet)
        elif selection == "8":
            set_name(wallet)
        elif selection == "9":
            print(wallet.export_puzzle_generator()(0))
            print(wallet.export_puzzle_generator()(1))
            print(wallet.export_puzzle_generator()(2))


run = asyncio.get_event_loop().run_until_complete
run(main())
