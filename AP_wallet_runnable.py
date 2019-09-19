import asyncio
import clvm
import qrcode
from chiasim.wallet.ap_wallet import APWallet
from chiasim.clients.ledger_sim import connect_to_ledger_sim
from chiasim.wallet.deltas import additions_for_body, removals_for_body
from chiasim.hashable import Coin
from chiasim.hashable.Body import BodyList
from clvm_tools import binutils
from chiasim.hashable import Program, ProgramHash, BLSSignature
from chiasim.puzzles.puzzle_utilities import pubkey_format, signature_from_string, puzzlehash_from_string
from binascii import hexlify


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
    if wallet.puzzle_generator_id == "1ea50e9399e360c85c240e9d17c5d11ccb8fbf37b0ee6e551282ddd5b5613206":
        print("Awaiting initial coin...")
    else:
        print("Puzzle Generator: ")
        print(wallet.puzzle_generator)
        print("Generator hash identifier:")
        print(wallet.puzzle_generator_id)
    print("New pubkey: ")
    pubkey = pubkey_format(wallet.get_next_public_key())
    print(pubkey)


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


def make_payment(wallet, approved_puzhash_sig_pairs):
    amount = -1
    if wallet.current_balance <= 0:
        print("You need some money first")
        return None
    print("Select a contact from approved list: ")
    for name in approved_puzhash_sig_pairs:
        print(" - " + name)
    name = input("Name of payee: ")

    if name not in approved_puzhash_sig_pairs:
        print("invalid contact")
        return

    while amount > wallet.current_balance or amount < 0:
        amount = int(input("Amount: "))
        if amount == "q":
            return

    puzzlehash = approved_puzhash_sig_pairs[name][0]
    return wallet.ap_generate_signed_transaction([(puzzlehash, amount)], [BLSSignature(approved_puzhash_sig_pairs[name][1])])


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


def ap_settings(wallet, approved_puzhash_sig_pairs):
    print("1: Add Authorised Payee")
    print("2: Change initialisation settings")
    choice = input()
    if choice == "1":
        print()
        name = input("Payee name: ")
        puzzle = input("Approved puzzlehash: ")
        puzhash = puzzlehash_from_string(puzzle)
        sig = input("Signature for puzzlehash: ")
        signature = signature_from_string(sig)
        approved_puzhash_sig_pairs[name] = (puzhash, signature)
        choice = input("Press 'c' to add another, or 'q' to return to menu: ")
    elif choice == "2":
        print("WARNING: This is only for if you messed it up the first time.")
        print("If you have already configured this properly, press 'q' to go back.")
        print("Please enter AP puzzlehash: ")
        AP_puzzlehash = input()
        if AP_puzzlehash == "q":
            return
        print("Please enter sender's pubkey: ")
        a_pubkey = input()
        if a_pubkey == "q":
            return
        wallet.set_sender_values(AP_puzzlehash, a_pubkey)
        print("Please enter signature for change making: ")
        signature = input()
        sig = signature_from_string(signature)
        wallet.set_approved_change_signature(sig)


async def main():
    ledger_api = await connect_to_ledger_sim("localhost", 9868)
    selection = ""
    wallet = APWallet()
    approved_puzhash_sig_pairs = {}  # 'name': (puzhash, signature)
    most_recent_header = None
    print("Welcome to AP Wallet")
    print("Your pubkey is: " + pubkey_format(wallet.get_next_public_key()))
    print("Please fill in some initialisation information (this can be changed later)")
    print("Please enter AP puzzlehash: ")
    AP_puzzlehash = input()
    print("Please enter sender's pubkey: ")
    a_pubkey = input()
    wallet.set_sender_values(AP_puzzlehash, a_pubkey)
    print("Please enter signature for change making: ")
    signature = input()
    sig = signature_from_string(signature)
    wallet.set_approved_change_signature(sig)

    while selection != "q":
        print("Select a function:")
        print("1: View Funds")
        print("2: Add Contact (DISABLED)")
        print("3: Make Payment")
        print("4: View Contacts (DISABLED)")
        print("5: Get Update")
        print("6: *GOD MODE* Commit Block / Get Money")
        print("7: Print my details for somebody else")
        print("8: Set my wallet detail")
        print("9: Make QR code")
        print("10: AP Settings / Register New Payee")

        print("q: Quit")
        selection = input()
        if selection == "1":
            view_funds(wallet)
        elif selection == "2":
            # add_contact(wallet)
            print("contacts temporarily disable")
        elif selection == "3":
            r = make_payment(wallet, approved_puzhash_sig_pairs)
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
            ap_settings(wallet, approved_puzhash_sig_pairs)


run = asyncio.get_event_loop().run_until_complete
run(main())
