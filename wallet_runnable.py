import asyncio
import clvm
import qrcode
from pyzbar.pyzbar import decode
from PIL import Image
from chiasim.wallet.wallet import Wallet
from chiasim.clients.ledger_sim import connect_to_ledger_sim
from chiasim.wallet.deltas import additions_for_body, removals_for_body
from chiasim.hashable import Coin
from chiasim.hashable.Body import BodyList
from clvm_tools import binutils
from chiasim.hashable import Program, ProgramHash
from binascii import hexlify
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
    pubkey = "%s" % hexlify(
        wallet.get_next_public_key().serialize()).decode('ascii')
    print(pubkey)
    print("Generator hash identifier:")
    print(wallet.puzzle_generator_id)
    print("Single string: " + wallet.name + ":" +
          wallet.puzzle_generator_id + ":" + pubkey)


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
    fn = input("Input file name: ")
    img.save(fn + ".jpg")
    print("QR code created in '" + fn + ".jpg'")


def read_qr(wallet):
    amount = -1
    if wallet.current_balance <= 0:
        print("You need some money first")
        return None
    print("Input filename of QR code: ")  # this'll have to do for now
    fn = input()
    decoded = decode(Image.open(fn))
    name, type, pubkey = QR_string_parser(str(decoded[0].data))
    if type not in wallet.generator_lookups:
        print("Unknown generator - please input the source.")
        source = input("Source: ")
        if str(ProgramHash(Program(binutils.assemble(source)))) != "0x" + type:
            print("source not equal to ID")
            breakpoint()
            return
        else:
            wallet.generator_lookups[type] = source
    while amount > wallet.current_balance or amount <= 0:
        amount = int(input("Amount: "))
    args = binutils.assemble("(0x" + pubkey + ")")
    program = Program(clvm.eval_f(clvm.eval_f, binutils.assemble(
        wallet.generator_lookups[type]), args))
    puzzlehash = ProgramHash(program)
    return wallet.generate_signed_transaction(amount, puzzlehash)


def QR_string_parser(input):
    arr = input.split(":")
    name = arr[0]
    generatorID = arr[1]
    pubkey = arr[2]
    if pubkey.endswith("'"):
        pubkey = pubkey[:-1]
    return name, generatorID, pubkey


def set_name(wallet):
    selection = input("Enter a new name: ")
    wallet.set_name(selection)


def make_payment(wallet):
    amount = -1
    if wallet.current_balance <= 0:
        print("You need some money first")
        return None
    qr = input("Enter QR string: ")
    name, type, pubkey = QR_string_parser(qr)
    if type not in wallet.generator_lookups:
        print("Unknown generator - please input the source.")
        source = input("Source: ")
        if str(ProgramHash(Program(binutils.assemble(source)))) != type:
            print("source not equal to ID")
            breakpoint()
            return
        else:
            wallet.generator_lookups[type] = source
    while amount > wallet.current_balance or amount < 0:
        amount = int(input("Amount: "))
    args = binutils.assemble("(0x" + pubkey + ")")
    program = Program(clvm.eval_f(clvm.eval_f, binutils.assemble(
        wallet.generator_lookups[type]), args))
    puzzlehash = ProgramHash(program)
    # print(puzzlehash)
    # breakpoint()
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
        # TODO: add a format checker to input here (and everywhere tbh)
        # Actual puzzle lockup/spend
        a_pubkey = wallet.get_next_public_key().serialize()
        b_pubkey = input("Enter recipient's pubkey: 0x")
        amount = input("Enter amount to give recipient: ")
        amount = int(amount)
        APpuzzlehash = ap_wallet_a_functions.ap_get_new_puzzlehash(
            a_pubkey, b_pubkey)
        spend_bundle = wallet.generate_signed_transaction(amount, APpuzzlehash)
        await ledger_api.push_tx(tx=spend_bundle)
        print()
        print("AP Puzzlehash is: " + str(APpuzzlehash))
        print("Pubkey used is: " + hexlify(a_pubkey).decode('ascii'))
        sig = ap_wallet_a_functions.ap_sign_output_newpuzzlehash(
            APpuzzlehash, wallet, a_pubkey)
        print("Approved change signature is: " + str(sig.sig))
        print("Single string: " + str(APpuzzlehash) + ":" +
              hexlify(a_pubkey).decode('ascii') + ":" + str(sig.sig))
        #pair = sig.aggsig_pair(BLSPublicKey(a_pubkey), APpuzzlehash)
        # print(sig.validate([pair]))

        # Authorised puzzle printout for AP Wallet
        print("Enter pubkeys of authorised recipients, press 'q' to finish")
        while choice != "q":
            singlestr = input("Enter recipient QR string: ")
            if singlestr == "q":
                return
            name, type, pubkey = QR_string_parser(singlestr)
            if type not in wallet.generator_lookups:
                print("Unknown generator - please input the source.")
                source = input("Source: ")
                if str(ProgramHash(Program(binutils.assemble(source)))) != type:
                    print("source not equal to ID")
                    breakpoint()
                    return
                else:
                    wallet.generator_lookups[type] = source
            args = binutils.assemble("(0x" + pubkey + ")")
            program = Program(clvm.eval_f(clvm.eval_f, binutils.assemble(
                wallet.generator_lookups[type]), args))
            puzzlehash = ProgramHash(program)
            print()
            #print("Puzzle: " + str(puzzlehash))
            sig = wallet.sign(puzzlehash, a_pubkey)
            #print("Signature: " + str(sig.sig))
            print("Single string for AP Wallet: " + name +
                  ":" + str(puzzlehash) + ":" + str(sig.sig))
            choice = input("Press 'c' to continue, or 'q' to quit to menu: ")


async def new_block(wallet, ledger_api):
    coinbase_puzzle_hash = wallet.get_new_puzzlehash()
    fees_puzzle_hash = wallet.get_new_puzzlehash()
    r = await ledger_api.next_block(coinbase_puzzle_hash=coinbase_puzzle_hash, fees_puzzle_hash=fees_puzzle_hash)
    body = r["body"]
    # breakpoint()
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
        print("2: Make Payment")
        print("3: Get Update")
        print("4: *GOD MODE* Commit Block / Get Money")
        print("5: Print my details for somebody else")
        print("6: Set my wallet name")
        print("7: Make QR code")
        print("8: Make Smart Contract")
        print("9: Payment to QR code")
        print("q: Quit")
        selection = input()
        if selection == "1":
            view_funds(wallet)
        elif selection == "2":
            r = make_payment(wallet)
            if r is not None:
                await ledger_api.push_tx(tx=r)
        elif selection == "3":
            await update_ledger(wallet, ledger_api, most_recent_header)
        elif selection == "4":
            most_recent_header = await new_block(wallet, ledger_api)
        elif selection == "5":
            print_my_details(wallet)
        elif selection == "6":
            set_name(wallet)
        elif selection == "7":
            make_QR(wallet)
        elif selection == "8":
            await select_smart_contract(wallet, ledger_api)
        elif selection == "9":
            r = read_qr(wallet)
            if r is not None:
                await ledger_api.push_tx(tx=r)


run = asyncio.get_event_loop().run_until_complete
run(main())
