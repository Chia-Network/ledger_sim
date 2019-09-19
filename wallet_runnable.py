import asyncio
import clvm
import qrcode
from chiasim.wallet.wallet import Wallet
from chiasim.clients.ledger_sim import connect_to_ledger_sim
from chiasim.wallet.deltas import additions_for_body, removals_for_body
from chiasim.hashable import Coin
from chiasim.hashable.Body import BodyList
from clvm_tools import binutils
from chiasim.hashable import Program, ProgramHash
from binascii import hexlify
from chiasim.puzzles.puzzle_utilities import pubkey_format
from chiasim.wallet import ap_wallet_a_functions


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
    print(wallet.puzzle_generator)
    print("New pubkey: ")
    pubkey = "0x%s" % hexlify(wallet.get_next_public_key().serialize()).decode('ascii')
    print(pubkey)
    print("Generator hash identifier:")
    print(wallet.puzzle_generator_id)


def make_QR(wallet):
    pubkey = hexlify(wallet.get_next_public_key().serialize()).decode('ascii')
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(wallet.name + ":" + wallet.puzzle_generator_id + ":" + pubkey)
    qr.make(fit=True)
    img = qr.make_image()
    img.save(pubkey+".jpg")
    print("QR code created in " + pubkey + ".jpg")


def set_name(wallet):
    selection = input("Enter a new name: ")
    wallet.set_name(selection)


def make_payment(wallet):
    amount = -1
    if wallet.current_balance <= 0:
        print("You need some money first")
        return None
    name = input("Name of payee: ")
    type = input("Generator hash ID: 0x")
    if type not in wallet.generator_lookups:
        print("Unknown generator - please input the source.")
        source = input("Source: ")
        if str(ProgramHash(Program(binutils.assemble(source)))) != "0x"+type:
            print("source not equal to ID")
            breakpoint()
            return
        else:
            wallet.generator_lookups[type] = source
    while amount > wallet.current_balance or amount < 0:
        amount = int(input("Amount: "))
    pubkey = input("Pubkey: 0x")
    args = binutils.assemble("(0x" + pubkey + ")")
    program = Program(clvm.eval_f(clvm.eval_f, binutils.assemble(wallet.generator_lookups[type]), args))
    puzzlehash = ProgramHash(program)
    print(puzzlehash)
    breakpoint()
    return wallet.generate_signed_transaction(amount, puzzlehash)


async def select_smart_contract(wallet, ledger_api):
    print("Select a smart contract: ")
    print("1: Authorised Payees")
    print("2: Add a new smart contract")
    choice = input()
    if choice == "1":
        if wallet.current_balance <= 0:
            print("You need some money first")
            return None
        # TODO: add a pubkey format checker to this (and everything tbh)
        # Actual puzzle lockup/spend
        approved_pubkeys = []
        a_pubkey = wallet.get_next_public_key().serialize()
        b_pubkey = input("Enter recipient's pubkey: 0x")
        amount = input("Enter amount to give recipient: ")
        amount = int(amount)
        APpuzzlehash = ap_wallet_a_functions.ap_get_new_puzzlehash(a_pubkey, b_pubkey)
        spend_bundle = wallet.generate_signed_transaction(amount, APpuzzlehash)
        await ledger_api.push_tx(tx=spend_bundle)
        print()
        print("AP Puzzlehash is: " + str(APpuzzlehash))
        print("Pubkey used is: " + pubkey_format(a_pubkey))
        sig = ap_wallet_a_functions.ap_sign_output_newpuzzlehash(APpuzzlehash, wallet, a_pubkey).sig
        print("Approved change signature is: " + str(sig))
        print("DEBUG bytes of sig: ")
        print(sig)

        # Authorised puzzle printout for AP Wallet
        print("Enter pubkeys of authorised recipients, press 'q' to finish")
        while choice != "q":
            name = input("Name of recipient: ")
            choice = input("Pubkey: 0x")
            if choice != "q":
                approved_pubkeys.append((name, choice))

        for pubkey in approved_pubkeys:
            puzzle = ProgramHash(wallet.puzzle_for_pk(pubkey[1]))
            print("Name: " + name)
            print("Puzzle: " + str(puzzle))
            print("Signature: " + str(wallet.sign(puzzle).sig))


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
        print(additions)
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
        print("2: Add Contact (DISABLED)")
        print("3: Make Payment")
        print("4: View Contacts (DISABLED)")
        print("5: Get Update")
        print("6: *GOD MODE* Commit Block / Get Money")
        print("7: Print my details for somebody else")
        print("8: Set my wallet name")
        print("9: Make QR code")
        print("10: Make Smart Contract")
        print("q: Quit")
        selection = input()
        if selection == "1":
            view_funds(wallet)
        elif selection == "2":
            # add_contact(wallet)
            print("contacts temporarily disable")
        elif selection == "3":
            r = make_payment(wallet)
            if r is not None:
                await ledger_api.push_tx(tx=r)
        elif selection == "4":
            # view_contacts(wallet)
            print("contacts temporarily disable")
        elif selection == "5":
            await update_ledger(wallet, ledger_api, most_recent_header)
        elif selection == "6":
            most_recent_header = await new_block(wallet, ledger_api)
        elif selection == "7":
            print_my_details(wallet)
        elif selection == "8":
            set_name(wallet)
        elif selection == "9":
            make_QR(wallet)
        elif selection == "10":
            await select_smart_contract(wallet, ledger_api)


run = asyncio.get_event_loop().run_until_complete
run(main())
