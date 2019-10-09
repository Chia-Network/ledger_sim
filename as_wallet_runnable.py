import asyncio
import clvm
import qrcode
from chiasim.wallet.as_wallet import ASWallet
from chiasim.clients.ledger_sim import connect_to_ledger_sim
from chiasim.wallet.deltas import additions_for_body, removals_for_body
from chiasim.hashable import Coin
from chiasim.hashable.Body import BodyList
from clvm_tools import binutils
from chiasim.hashable import Program, ProgramHash, BLSSignature
from chiasim.puzzles.puzzle_utilities import pubkey_format, signature_from_string, puzzlehash_from_string, BLSSignature_from_string
from binascii import hexlify
from chiasim.validation import ChainView


def print_my_details(wallet):
    print()
    print(divider)
    print(" \u2447 Wallet Details \u2447")
    print()
    print("Name: " + wallet.name)
    print("New pubkey: "+ pubkey_format(wallet.get_next_public_key()))
    choice = "edit"
    while choice == "edit":
        print()
        print("Would you like to edit your wallet's name (type 'name'), generate a new pubkey (type 'pubkey'), or return to the menu (type 'menu')?")
        choice = input(prompt)
        if choice == "name":
            while choice == "name":
                print()
                print("Enter a new name for your wallet:")
                name_new = input(prompt)
                if name_new == "":
                    print()
                    print("Your wallet's name cannot be blank.")
                    choice = "invalid"
                    while choice == "invalid":
                        print()
                        print("Would you like to enter a new name (type 'name') or return to the menu (type 'menu')?")
                        choice = input(prompt)
                        if choice == "menu":
                            print(divider)
                            return
                        if choice != "name":
                            choice = "invalid"
                            print()
                            print("You entered an invalid selection.")
                wallet.set_name(name_new)
                print()
                print("Your wallet's name has been changed.")
                choice = "edit"
        elif choice == "pubkey":
            print()
            print("New pubkey: "+ pubkey_format(wallet.get_next_public_key()))
            choice = "edit"
        elif choice == "menu":
            print(divider)
            return
        else:
            print()
            print("You entered an invalid selection.")
            choice = "edit"
    print(divider)


def view_funds(wallet, as_swap_list):
    print()
    print(divider)
    print(" \u2447 View Funds \u2447")
    puzzlehashes = []
    for swap in as_swap_list:
        puzzlehashes.append(swap["puzzlehash"])
    coins = [x.amount if hexlify(x.puzzle_hash).decode('ascii') not in puzzlehashes else "{}{}".format("*", x.amount) for x in wallet.my_utxos]
    if coins == []:
        print()
        print("Your coins:")
        print("[ NO COINS ]")
    else:
        print()
        print("Your coins: ")
        print(coins)
    print(divider)


def view_contacts(as_contacts):
    print()
    print("Your contacts:")
    if as_contacts == {}:
        print("- NO CONTACTS -")
    else:
        for name in as_contacts:
            print("\u2448 " + name)


def view_contacts_details(as_contacts):
    print()
    print(divider)
    print(" \u2447 View Contacts \u2447")
    choice = "view"
    while choice == "view":
        view_contacts(as_contacts)
        if as_contacts == {}:
            print(divider)
            return
        choice = "invalid"
        while choice == "invalid":
            print()
            print("Type the name of a contact to see their contact details or type 'menu' to return to menu:")
            name = input(prompt)
            if name == "menu":
                print(divider)
                return
            elif name in as_contacts:
                print()
                print("Name: " + name)
                print("Pubkey: " + as_contacts[name][0])
                print("AS coin puzzlehashes:", ', '.join(as_contacts[name][1]))
            else:
                print()
                print("That name is not in your contact list.")
            choice = "invalid"
            while choice == "invalid":
                print()
                print("Type 'view' to see the details of another contact, or 'menu' to return to menu:")
                choice = input(prompt)
                if choice == "menu":
                    print(divider)
                    return
                elif choice != "view":
                    choice = "invalid"
                    print()
                    print("You entered an invalid selection.")


def add_contact(wallet, as_contacts):
    print()
    print(divider)
    print(" \u2447 Add Contact \u2447")
    choice = "add"
    while choice == "add":
        print()
        print("Contact name:")
        name = input(prompt)
        while name == "":
            print()
            print("Contact name cannot be blank.")
            print()
            print("Please enter a contact name or type 'menu' to return to menu:")
            name = input(prompt)
            if name == "menu":
                print(divider)
                return
        print("Contact pubkey (type 'none' if not yet established):")
        pubkey = input(prompt)
        choice = "invalid"
        while choice == "invalid":
            try:
                hexval = int(pubkey, 16)
                if len(pubkey) != 96:
                    print()
                    print("This is not a valid pubkey. Please enter a valid pubkey or type 'menu' to return to menu: ")
                    pubkey = input(prompt)
                    if pubkey == "menu":
                        print(divider)
                        return
                else:
                    choice = "add"
            except:
                print()
                print("This is not a valid pubkey. Please enter a valid pubkey or type 'menu' to return to menu: ")
                pubkey = input(prompt)
                if pubkey == "menu":
                    print(divider)
                    return
        as_contacts[name] = [pubkey, []]
        print()
        print("{} {}".format(name, "has been added to your contact list."))
        choice = "invalid"
        while choice == "invalid":
            print()
            print("Type 'add' to add another contact, or 'menu' to return to menu:")
            choice = input(prompt)
            if choice == "menu":
                print(divider)
                return
            elif choice != "add":
                choice = "invalid"
                print()
                print("You entered an invalid selection.")


def edit_contact(wallet, as_contacts):
    print()
    print(divider)
    print(" \u2447 Edit Contact \u2447")
    choice = "edit"
    while choice == "edit":
        view_contacts(as_contacts)
        if as_contacts == {}:
            print()
            print("There are no available contacts to edit because your contact list is empty.")
            return
        else:
            print()
            print("Type the name of the contact you'd like to edit:")
            name = input(prompt)
            if name not in as_contacts:
                print()
                print("The name you entered is not in your contacts list.")
                choice = "invalid"
                while choice == "invalid":
                    print()
                    print("Type 'edit' to enter a different name, or 'menu' to return to menu:")
                    choice = input(prompt)
                    if choice == "menu":
                        print(divider)
                        return
                    elif choice != "edit":
                        choice = "invalid"
                        print()
                        print("You entered an invalid selection.")
            else:
                choice = "option"
                while choice == "option":
                    print()
                    print("Name: " + name)
                    print("Pubkey: " + as_contacts[name][0])
                    print("AS coin puzzlehashes:", ', '.join(as_contacts[name][1]))
                    print()
                    print("Would you like to edit the name (type 'name') or the pubkey (type 'pubkey') for this contact? (Or type 'menu' to return to the menu.)")
                    choice = input(prompt)
                    if choice == "name":
                        print()
                        print("Enter the new name for this contact or type 'menu' to return to the menu:")
                        name_new = input(prompt)
                        while name_new == "":
                            print()
                            print("Contact name cannot be blank.")
                            print()
                            print("Enter the new name for this contact or type 'menu' to return to the menu:")
                            name_new = input(prompt)
                        if name_new == "menu":
                            print(divider)
                            return
                        as_contacts[name_new] = as_contacts.pop(name)
                        print()
                        print("{}{}".format(name_new, "'s name has been updated."))
                    elif choice == "pubkey":
                        print()
                        print("Enter the new pubkey for this contact or type 'menu' to return to the menu:")
                        pubkey_new = input(prompt)
                        if pubkey_new == "menu":
                            print(divider)
                            return
                        choice = "invalid"
                        while choice == "invalid":
                            try:
                                hexval = int(pubkey_new, 16)
                                if len(pubkey_new) != 96:
                                    print()
                                    print("This is not a valid pubkey.")
                                    print()
                                    print("Please enter a valid pubkey or type 'menu' to return to menu:")
                                    pubkey_new = input(prompt)
                                    if pubkey_new == "menu":
                                        print(divider)
                                        return
                                else:
                                    choice = "edit"
                            except:
                                print()
                                print("This is not a valid pubkey.")
                                print()
                                print("Please enter a valid pubkey or type 'menu' to return to menu:")
                                pubkey_new = input(prompt)
                                if pubkey_new == "menu":
                                    print(divider)
                                    return
                        as_contacts[name][0] = pubkey_new
                        print()
                        print("{}{}".format(name, "'s pubkey has been updated."))
                    elif choice == "menu":
                        print(divider)
                        return
                    else:
                        choice = "option"
                        print()
                        print("You entered an invalid selection.")
                choice = "invalid"
                while choice == "invalid":
                    print()
                    print("Type 'edit' to add another contact, or 'menu' to return to menu:")
                    choice = input(prompt)
                    if choice == "menu":
                        print(divider)
                        return
                    elif choice != "edit":
                        choice = "invalid"
                        print()
                        print("You entered an invalid selection.")


def view_current_atomic_swaps(as_swap_list):
    print()
    print(divider)
    print(" \u2447 View Current Atomic Swaps \u2447")
    view_swaps(as_swap_list)
    print(divider)


def view_swaps(as_swap_list):
    if as_swap_list == []:
        print()
        print("You are not currently participating in any atomic swaps.")
    else:
        print()
        print("Your current atomic swaps:")
        for swap in as_swap_list:
            print("\u29a7")
            print("{} {}".format("Atomic swap puzzlehash:", swap["puzzlehash"]))
            print("{} {}".format("Atomic swap partner:", swap["swap partner"]))
            print("{} {}".format("Atomic swap partner pubkey:", swap["partner pubkey"]))
            print("{} {}".format("Atomic swap amount:", swap["amount"]))
            print("{} {}".format("Atomic swap timelock time:", swap["timelock"]))
            print("{} {}".format("Atomic swap secret:", swap["secret"]))
            print("{} {}".format("Atomic swap spend method available:", swap["spend method"]))
            print("\u29a6")


def set_partner(wallet, as_contacts):
    view_contacts(as_contacts)
    if as_contacts == {}:
        print()
        print("Your contact list is empty. Pleast add your intended atomic swap partner to your contact list before initiating an atomic swap.")
        return "menu"
    else:
        print()
        print("Choose a contact for the atomic swap:")
        swap_partner = input(prompt)
        for c in as_contacts:
            if swap_partner in as_contacts:
                return swap_partner
            else:
                print()
                print("Invalid input: This contact is not in your contact list.")
                return None


def set_amount(wallet, as_contacts, method):
    print()
    print("Your coins: ", [x.amount for x in wallet.my_utxos])
    print()
    if method == "init":
        print("Enter the amount you'd like to swap:")
        amount = input(prompt)
    elif method == "add":
        print("Enter the amount being swapped:")
        amount = input(prompt)
    try:
        amount = int(amount)
    except ValueError:
        print()
        print("Invalid input: You entered an invalid amount.")
        return None
    if amount <= 0:
        print()
        print("Invalid input: The amount must be greater than 0.")
        return None
    elif wallet.current_balance <= amount:
        print()
        print("Invalid input: This amount exceeds your wallet balance.")
        return None
    else:
        return amount


def set_timelock(wallet, as_contacts):
    print()
    print("Enter the timelock time for the atomic swap:")
    time = input(prompt)
    try:
        timelock = int(time)
    except ValueError:
        print()
        print("Invalid input: You entered an invalid timelock time.")
        return None
    if timelock <= 0:
        print()
        print("Invalid input: Timelock time must be greater than 0.")
        return None
    else:
        return timelock


def set_secret(method):
    if method == "init":
        print()
        print("Enter a secret to hashlock the atomic swap coin:")
        secret = input(prompt)
        if secret == "":
            print()
            print("Invalid input: The secret cannot be left blank.")
            return None
        elif secret == "unknown":
            print()
            print("Invalid input: You may not use \"unknown\" as your secret.")
            return None
    elif method == "add":
        print()
        print("(Optional) If you know it, enter the hashlock secret for this atomic swap coin (or leave blank and press 'return'): ")
        secret = input(prompt)
        if secret == "":
            secret = "unknown"
    return secret


def set_parameters_init(wallet, as_contacts):
    choice = "partner"
    menu = None
    while choice == "partner":
        swap_partner = set_partner(wallet, as_contacts)
        if swap_partner == "menu":
            return None, None, None, None, None, "menu"
        elif swap_partner == None:
            choice = "invalid"
            while choice == "invalid":
                print()
                print("Type 'partner' to choose a new partner for the atomic swap, or 'menu' to return to menu:")
                choice = input(prompt)
                if choice == "menu":
                    return None, None, None, None, None, "menu"
                elif choice != "partner":
                    choice = "invalid"
                    print()
                    print("You entered an invalid selection.")
        else:
            partner_pubkey = as_contacts[swap_partner][0]
            choice = "continue"
    choice = "amount"
    while choice == "amount":
        amount = set_amount(wallet, as_contacts, "init")
        if amount == None:
            choice = "invalid"
            while choice == "invalid":
                print()
                print("Type 'amount' to enter a new amount, or 'menu' to return to menu:")
                choice = input(prompt)
                if choice == "menu":
                    return None, None, None, None, None, "menu"
                elif choice != "amount":
                    choice = "invalid"
                    print()
                    print("You entered an invalid selection.")
        else:
            choice = "continue"
    choice = "time"
    while choice == "time":
        timelock = set_timelock(wallet, as_contacts)
        if timelock == None:
            choice = "invalid"
            while choice == "invalid":
                print()
                print("Type 'time' to enter a new timelock time, or 'menu' to return to menu:")
                choice = input(prompt)
                if choice == "menu":
                    return None, None, None, None, None, "menu"
                elif choice != "time":
                    choice = "invalid"
                    print()
                    print("You entered an invalid selection.")
        else:
            choice = "continue"
    choice = "secret"
    while choice == "secret":
        secret = set_secret("init")
        if secret == None:
            choice = "invalid"
            while choice == "invalid":
                print()
                print("Type 'secret' to enter a new secret, or 'menu' to return to menu: ")
                choice = input(prompt)
                if choice == "menu":
                    return None, None, None, None, None, "menu"
                elif choice != "secret":
                    choice = "invalid"
                    print()
                    print("You entered an invalid selection.")
        else:
            choice = "continue"
    return swap_partner, partner_pubkey, amount, timelock, secret, menu


def init_swap(wallet, as_contacts, as_swap_list, my_pubkey_orig):
    print()
    print(divider)
    print(" \u2447 Initiate Atomic Swap \u2447")
    swap_partner, partner_pubkey, amount, timelock, secret, menu = set_parameters_init(wallet, as_contacts)
    if menu == "menu":
        print(divider)
        return
    my_pubkey = wallet.get_next_public_key().serialize()
    secret_hash = wallet.as_generate_secret_hash(secret)
    puzzlehash = wallet.as_get_new_puzzlehash(my_pubkey_orig, bytes.fromhex(partner_pubkey), amount, timelock, secret_hash)
    spend_bundle = wallet.generate_signed_transaction(amount, puzzlehash)

    spend_method = "timelock"

    new_swap = {
            "puzzlehash" : hexlify(puzzlehash).decode('ascii'),
    		"swap partner" : swap_partner,
    		"partner pubkey" : partner_pubkey,
    		"amount" : amount,
    		"timelock" : timelock,
    		"secret" : secret,
            "spend method" : spend_method
    	}
    as_swap_list.append(new_swap)
    as_contacts[swap_partner][1].append(hexlify(puzzlehash).decode('ascii'))

    print()
    print("You have initiating the following atomic swap:")
    print("{} {}".format("Atomic swap puzzlehash:", new_swap["puzzlehash"]))
    print("{} {}".format("Atomic swap partner:", new_swap["swap partner"]))
    print("{} {}".format("Atomic swap partner pubkey:", new_swap["partner pubkey"]))
    print("{} {}".format("Atomic swap amount:", new_swap["amount"]))
    print("{} {}".format("Atomic swap timelock time:", new_swap["timelock"]))
    print("{} {}".format("Atomic swap secret:", new_swap["secret"]))
    print("{} {}".format("Atomic swap spend method available:", new_swap["spend method"]))
    print(divider)
    return spend_bundle


def add_puzzlehash(wallet):
    print()
    print("Enter the puzzlehash for this atomic swap:")
    puzzlehash = input(prompt)
    if puzzlehash == "":
        print()
        print("Invalid input: The puzzlehash cannot be left blank.")
        return None
    try:
        hexval = int(puzzlehash, 16)
        if len(puzzlehash) != 64:
            print()
            print("Invalid input: You did not enter a valid puzzlehash.")
            return None
    except:
        print()
        print("Invalid input: You did not enter a valid puzzlehash.")
        return None
    return puzzlehash


def set_parameters_add(wallet, as_contacts, as_swap_list):
    choice = "partner"
    menu = None
    while choice == "partner":
        swap_partner = set_partner(wallet, as_contacts)
        if swap_partner == None:
            choice = "invalid"
            while choice == "invalid":
                print()
                print("Type 'partner' to choose a new partner for the atomic swap, or 'menu' to return to menu:")
                choice = input(prompt)
                if choice == "menu":
                    return None, None, None, None, None, None, "menu"
                elif choice != "partner":
                    choice = "invalid"
                    print()
                    print("You entered an invalid selection.")
        else:
            partner_pubkey = as_contacts[swap_partner][0]
            choice = "continue"
    choice = "amount"
    while choice == "amount":
        amount = set_amount(wallet, as_contacts, "add")
        if amount == None:
            choice = "invalid"
            while choice == "invalid":
                print()
                print("Type 'amount' to enter a new amount, or 'menu' to return to menu:")
                choice = input(prompt)
                if choice == "menu":
                    return None, None, None, None, None, None, "menu"
                elif choice != "amount":
                    choice = "invalid"
                    print()
                    print("You entered an invalid selection.")
        else:
            choice = "continue"
    choice = "time"
    while choice == "time":
        timelock = set_timelock(wallet, as_contacts)
        if timelock == None:
            choice = "invalid"
            while choice == "invalid":
                print()
                print("Type 'time' to enter a new timelock time, or 'menu' to return to menu:")
                choice = input(prompt)
                if choice == "menu":
                    return None, None, None, None, None, None, "menu"
                elif choice != "time":
                    choice = "invalid"
                    print()
                    print("You entered an invalid selection.")
        else:
            choice = "continue"
    secret = set_secret("add")
    choice = "puzzlehash"
    while choice == "puzzlehash":
        puzzlehash = add_puzzlehash(wallet)
        if puzzlehash == None:
            choice = "invalid"
            while choice == "invalid":
                print()
                print("Type 'puzzlehash' to enter a new puzzlehash, or 'menu' to return to menu:")
                choice = input(prompt)
                if choice == "menu":
                    return None, None, None, None, None, None, "menu"
                elif choice != "puzzlehash":
                    choice = "invalid"
                    print()
                    print("You entered an invalid selection.")
        else:
            choice = "continue"
    return swap_partner, partner_pubkey, amount, timelock, secret, puzzlehash, menu


def add_swap(wallet, as_contacts, as_swap_list):
    print()
    print(divider)
    print(" \u2447 Add Atomic Swap \u2447")
    swap_partner, partner_pubkey, amount, timelock, secret, puzzlehash, menu = set_parameters_add(wallet, as_contacts, as_swap_list)
    if menu == "menu":
        print(divider)
        return

    spend_method = "secret"

    new_swap = {
    		"puzzlehash" : puzzlehash,
            "swap partner" : swap_partner,
    		"partner pubkey" : partner_pubkey,
    		"amount" : amount,
    		"timelock" : timelock,
    		"secret" : secret,
            "spend method" : spend_method
    	}
    as_swap_list.append(new_swap)
    as_contacts[swap_partner][1].append(puzzlehash)

    print()
    print("You have added the following atomic swap:")
    print("{} {}".format("Atomic swap puzzlehash:", new_swap["puzzlehash"]))
    print("{} {}".format("Atomic swap partner:", new_swap["swap partner"]))
    print("{} {}".format("Atomic swap partner pubkey:", new_swap["partner pubkey"]))
    print("{} {}".format("Atomic swap amount:", new_swap["amount"]))
    print("{} {}".format("Atomic swap timelock time:", new_swap["timelock"]))
    print("{} {}".format("Atomic swap secret:", new_swap["secret"]))
    print("{} {}".format("Atomic swap spend method available:", new_swap["spend method"]))
    print(divider)
    return


def find_coin(as_swap_list):
    choice = "find"
    while choice == "find":
        view_swaps(as_swap_list)
        print()
        print("Enter the puzzlehash for the atomic swap coin you wish to spend:")
        puzzlehash = input(prompt)
        for swap in as_swap_list:
            if puzzlehash == str(swap["puzzlehash"]):
                return as_swap_list.index(swap)
            else:
                print()
                print("The puzzlehash you entered is not in your list of available atomic swaps.")
                choice = "invalid"
                while choice == "invalid":
                    print()
                    print("Type 'puzzlehash' to enter a new puzzlehash, or 'menu' to return to menu:")
                    choice = input(prompt)
                    if choice == "menu":
                        return
                    elif choice == "puzzlehash":
                        choice = "find"
                    elif choice != "puzzlehash":
                        choice = "invalid"
                        print()
                        print("You entered an invalid selection.")


def update_secret(as_swap_list, swap_index):
    swap = as_swap_list[swap_index]
    if swap["secret"] == "unknown":
        choice = "secret"
        while choice == "secret":
            print()
            print("You do not have a secret on file for this atomic swap. Would you like to enter one now? (y/n)")
            response = input(prompt)
            if response == "y":
                choice = "continue"
            elif response == "n":
                print()
                print("A secret is required to spend this atomic swap coin. Please try again when you know the secret.")
                return "menu"
            else:
                print()
                print("You entered an invalid selection.")
        choice = "secret"
        while choice == "secret":
            print()
            print("Enter the secret for this atomic swap:")
            new_secret = input(prompt)
            if new_secret == "":
                print()
                print("You did not enter a secret. A secret is required to spend this atomic swap coin.")
                choice = "invalid"
                while choice == "invalid":
                    print()
                    print("Would you like to enter a secret now? (y/n)")
                    response = input(prompt)
                    if response == "y":
                        choice = "secret"
                    elif response == "n":
                        print()
                        print("A secret is required to spend this atomic swap coin. Please try again when you know the secret.")
                        return "menu"
                    else:
                        print()
                        print("You entered an invalid selection.")
            else:
                swap["secret"] = new_secret
                choice = "continue"
    else:
        print()
        print("Enter a new secret for this atomic swap:")
        new_secret = input(prompt)
        if new_secret == "":
            print()
            print("You did not enter a secret. A secret is required to spend this atomic swap coin.")
            choice = "invalid"
            while choice == "invalid":
                print()
                print("Would you like to enter a secret now? (y/n)")
                response = input(prompt)
                if response == "y":
                    choice = "secret"
                elif response == "n":
                    print()
                    print("A secret is required to spend this atomic swap coin. Please try again when you know the secret.")
                    return "menu"
                else:
                    print()
                    print("You entered an invalid selection.")
        else:
            swap["secret"] = new_secret
            choice = "continue"
    return


def spend_with_secret(wallet, as_swap_list, swap_index, my_pubkey_orig):
    swap = as_swap_list[swap_index]
    menu = update_secret(as_swap_list, swap_index)
    if menu == "menu" or swap["secret"] == "unknown":
        return
    choice = "secret"
    while choice == "secret":
        print()
        print("{} {}".format("The secret you have on file for this atomic swap is:", swap["secret"]))
        print()
        print("Would you like to use this secret to spend this atomic swap coin? (y/n)")
        response = input(prompt)
        if response == "y":
            choice = "continue"
        elif response == "n":
            choice = "invalid"
            while choice == "invalid":
                print()
                print("Would you like to update the secret now? (y/n)")
                response = input(prompt)
                if response == "y":
                    update_secret(as_swap_list, swap_index)
                    choice = "secret"
                elif response == "n":
                    print()
                    print("A secret is required to spend this atomic swap coin. Please try again when you know the secret.")
                    return
                else:
                    print()
                    print("You entered an invalid selection.")
        else:
            print()
            print("You entered an invalid selection.")
    my_pubkey = wallet.get_next_public_key().serialize()
    secret_hash = wallet.as_generate_secret_hash(swap["secret"])
    spend_bundle = wallet.as_create_spend_bundle(swap["puzzlehash"], swap["amount"], swap["timelock"], secret_hash, as_pubkey_sender = bytes.fromhex(swap["partner pubkey"]), as_pubkey_receiver = my_pubkey_orig, who = "receiver", as_sec_to_try = swap["secret"])
    return spend_bundle


def spend_with_timelock(wallet, as_swap_list, swap_index, my_pubkey_orig):
    swap = as_swap_list[swap_index]
    my_pubkey = wallet.get_next_public_key().serialize()
    secret_hash = wallet.as_generate_secret_hash(swap["secret"])
    spend_bundle = wallet.as_create_spend_bundle(swap["puzzlehash"], swap["amount"], swap["timelock"], secret_hash, as_pubkey_sender = my_pubkey_orig, as_pubkey_receiver = bytes.fromhex(swap["partner pubkey"]), who = "sender", as_sec_to_try = swap["secret"])
    return spend_bundle


def remove_swap_instances(wallet, as_contacts, as_swap_list, removals):
    for coin in removals:
        for swap in as_swap_list:
            if hexlify(coin.puzzle_hash).decode('ascii') == swap["puzzlehash"]:
                as_swap_list.remove(swap)
                as_contacts[swap["swap partner"]][1].remove(swap["puzzlehash"])


def spend_coin(wallet, as_contacts, as_swap_list, my_pubkey_orig):
    print()
    print(divider)
    print(" \u2447 Redeem Atomic Swap Coin \u2447")
    swap_index = find_coin(as_swap_list)
    if swap_index == None:
        print(divider)
        return
    swap = as_swap_list[swap_index]
    spend_method = swap["spend method"]
    if spend_method == "secret":
        spend_bundle = spend_with_secret(wallet, as_swap_list, swap_index, my_pubkey_orig)
    elif spend_method == "timelock":
        spend_bundle = spend_with_timelock(wallet, as_swap_list, swap_index, my_pubkey_orig)
    print(divider)
    return spend_bundle


async def update_ledger(wallet, ledger_api, most_recent_header, as_contacts, as_swap_list):
    if most_recent_header is None:
        r = await ledger_api.get_all_blocks()
    else:
        r = await ledger_api.get_recent_blocks(most_recent_header=most_recent_header)
    update_list = BodyList.from_bin(r)
    for body in update_list:
        additions = list(additions_for_body(body))
        removals = removals_for_body(body)
        removals = [Coin.from_bin(await ledger_api.hash_preimage(hash=x)) for x in removals]
        remove_swap_instances(wallet, as_contacts, as_swap_list, removals)
        wallet.notify(additions, removals, as_swap_list)
    print()
    print(divider)
    print(" \u2447 Get Update \u2447")
    puzzlehashes = []
    for swap in as_swap_list:
        puzzlehashes.append(swap["puzzlehash"])
    for coin in additions:
        for puzzlehash in puzzlehashes:
            if hexlify(coin.puzzle_hash).decode('ascii') == puzzlehash:
                print()
                print("An atomic swap coin is accessible to you.")
    print()
    print("Update complete.")
    print(divider)


async def new_block(wallet, ledger_api, as_contacts, as_swap_list):
    coinbase_puzzle_hash = wallet.get_new_puzzlehash()
    fees_puzzle_hash = wallet.get_new_puzzlehash()
    r = await ledger_api.next_block(coinbase_puzzle_hash=coinbase_puzzle_hash, fees_puzzle_hash=fees_puzzle_hash)
    body = r["body"]
    most_recent_header = r['header']
    additions = list(additions_for_body(body))
    removals = removals_for_body(body)
    removals = [Coin.from_bin(await ledger_api.hash_preimage(hash=x)) for x in removals]
    remove_swap_instances(wallet, as_contacts, as_swap_list, removals)
    wallet.notify(additions, removals, as_swap_list)
    print()
    print(divider)
    print(" \u2447 Commit Block \u2447")
    print()
    print("You have received a block reward.")
    puzzlehashes = []
    for swap in as_swap_list:
        puzzlehashes.append(swap["puzzlehash"])
    for coin in additions:
        for puzzlehash in puzzlehashes:
            if hexlify(coin.puzzle_hash).decode('ascii') == puzzlehash:
                print()
                print("An atomic swap coin is accessible to you.")
    print(divider)
    return most_recent_header


def print_leaf():
    print()
    print("\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff")
    print("\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u287f\u281f\u281b\u280b\u2809\u2809\u2809\u2809\u2809\u2809\u2809\u2819\u281b\u283b\u283f\u28bf\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff")
    print("\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u281f\u2801\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2808\u2809\u289b\u28ff\u28ff\u28ff")
    print("\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u281f\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2880\u28ff\u28ff\u28ff\u28ff")
    print("\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u280b\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2880\u28ff\u28ff\u28ff\u28ff\u28ff")
    print("\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u280f\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u28c0\u2860\u2814\u2802\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u28a0\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff")
    print("\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u2800\u2800\u2800\u2800\u2800\u28c0\u28e4\u28f6\u281e\u280b\u2801\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u28f0\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff")
    print("\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u2800\u28c0\u28f4\u28ff\u281f\u280b\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u28fc\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff")
    print("\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u287f\u281f\u2801\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u28a0\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff")
    print("\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u281f\u2801\u2880\u28c0\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2880\u28fe\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff")
    print("\u28ff\u28ff\u28ff\u28ff\u281f\u2881\u28e4\u28f6\u28ff\u28ff\u28ff\u28f7\u28c4\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u2800\u28e0\u28fe\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff")
    print("\u28ff\u28ff\u28ef\u28fe\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28f6\u28e6\u28e4\u28e4\u28e4\u28f4\u28f6\u28fe\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff")
    print("\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff\u28ff")


divider = "\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449\u2449"


prompt = "\u2446 "


async def main():
    ledger_api = await connect_to_ledger_sim("localhost", 9868)
    selection = ""
    wallet = ASWallet()
    as_contacts = {}  # 'name': (puzhash)
    as_swap_list = []
    most_recent_header = None
    print_leaf()
    print()
    print("Welcome to your Chia Atomic Swap Wallet.")
    print()
    my_pubkey_orig = wallet.get_next_public_key().serialize()
    print("Your pubkey is: " + hexlify(my_pubkey_orig).decode('ascii'))

    while selection != "q":
        print()
        print(divider)
        print(" \u2447 Menu \u2447")
        print()
        print("Select a function:")
        print("\u2448 1 Wallet Details")
        print("\u2448 2 View Funds")
        print("\u2448 3 View Contacts")
        print("\u2448 4 Add Contact")
        print("\u2448 5 Edit Contact")
        print("\u2448 6 View Current Atomic Swaps")
        print("\u2448 7 Initiate Atomic Swap")
        print("\u2448 8 Add Atomic Swap")
        print("\u2448 9 Redeem Atomic Swap Coin")
        print("\u2448 10 Get Update")
        print("\u2448 11 *GOD MODE* Commit Block / Get Money")
        print("\u2448 q Quit")
        print(divider)
        print()

        selection = input(prompt)
        if selection == "1":
            print_my_details(wallet)
        if selection == "2":
            view_funds(wallet, as_swap_list)
        elif selection == "3":
            view_contacts_details(as_contacts)
        elif selection == "4":
            add_contact(wallet, as_contacts)
        elif selection == "5":
            edit_contact(wallet, as_contacts)
        elif selection == "6":
            view_current_atomic_swaps(as_swap_list)
        elif selection == "7":
            spend_bundle = init_swap(wallet, as_contacts, as_swap_list, my_pubkey_orig)
            if spend_bundle is not None:
                await ledger_api.push_tx(tx=spend_bundle)
        elif selection == "8":
            add_swap(wallet, as_contacts, as_swap_list)
        elif selection == "9":
            spend_bundle = spend_coin(wallet, as_contacts, as_swap_list, my_pubkey_orig)
            if spend_bundle is not None:
                await ledger_api.push_tx(tx=spend_bundle)
        elif selection == "10":
            await update_ledger(wallet, ledger_api, most_recent_header, as_contacts, as_swap_list)
        elif selection == "11":
            most_recent_header = await new_block(wallet, ledger_api, as_contacts, as_swap_list)




run = asyncio.get_event_loop().run_until_complete
run(main())
