from chiasim.wallet.wallet import Wallet
import hashlib
import clvm
import sys
from chiasim.hashable import Program, ProgramHash, CoinSolution, SpendBundle, BLSSignature
from binascii import hexlify
from chiasim.validation.Conditions import (
    conditions_by_opcode, make_create_coin_condition, make_assert_my_coin_id_condition, make_assert_min_time_condition
)
from chiasim.hashable.Coin import Coin
from chiasim.hashable.CoinSolution import CoinSolutionList
from clvm_tools import binutils
from .BLSPrivateKey import BLSPrivateKey
from chiasim.validation.Conditions import ConditionOpcode
from chiasim.puzzles.p2_delegated_puzzle import puzzle_for_pk
from chiasim.validation.consensus import (
    conditions_for_solution, hash_key_pairs_for_conditions_dict
)
from chiasim.puzzles.puzzle_utilities import pubkey_format, puzzlehash_from_string, BLSSignature_from_string
from blspy import Signature
from chiasim.hack.keys import build_spend_bundle, sign_f_for_keychain


#ASWallet is subclass of Wallet
class ASWallet(Wallet):
    def __init__(self):
        super().__init__()
        return


    # special AS version of the standard get_keys function which allows both ...
    # ... parties in an atomic swap recreate an atomic swap puzzle which was ...
    # ... created by the other party
    def get_keys(self, hash, as_pubkey_sender = None, as_pubkey_receiver = None, as_amount = None, as_timelock_t = None, as_secret_hash = None):
        for child in reversed(range(self.next_address)):
            pubkey = self.extended_secret_key.public_child(child).get_public_key()
            if hash == ProgramHash(puzzle_for_pk(pubkey.serialize())):
                return (pubkey, self.extended_secret_key.private_child(child).get_private_key())
            elif as_pubkey_sender is not None and as_pubkey_receiver is not None and as_amount is not None and as_timelock_t is not None and as_secret_hash is not None:
                if hash == ProgramHash(self.as_make_puzzle(as_pubkey_sender, as_pubkey_receiver, as_amount, as_timelock_t, as_secret_hash)):
                    return (pubkey, self.extended_secret_key.private_child(child).get_private_key())


    def notify(self, additions, deletions, as_swap_list):
        super().notify(additions, deletions)
        puzzlehashes = []
        for swap in as_swap_list:
            puzzlehashes.append(swap["puzzlehash"])
        if puzzlehashes != []:
            self.as_notify(additions, puzzlehashes)

    def as_notify(self, additions, puzzlehashes):
        for coin in additions:
            for puzzlehash in puzzlehashes:
                if hexlify(coin.puzzle_hash).decode('ascii') == puzzlehash:
                    self.current_balance += coin.amount
                    self.my_utxos.add(coin)
                    return


    # needs to be adapted for potential future changes regarding how atomic ...
    # ... swap coins are integrated into wallets (right now the atomic swap ...
    # ... coins are added to an atomic swap wallet's utxo set but that ...
    # ... could change)
    def as_select_coins(self, amount, as_puzzlehash):
        if amount > self.current_balance:
            return None

        used_utxos = set()
        if isinstance(as_puzzlehash, str):
            as_puzzlehash = puzzlehash_from_string(as_puzzlehash)
        print(self.my_utxos)
        coins = self.my_utxos.copy()
        for coin in coins:
            if coin.puzzle_hash == as_puzzlehash:
                used_utxos.add(coin)
        return used_utxos


    # fake version
    def as_request(self, as_wallet_receiver, as_amount, as_timelock_t):
        print()
        print("Hi " + str(as_wallet_receiver) + ".")
        print("This is " + str(self) + ".")
        reply = input("Would you like to swap " + str(as_amount) + " coins with me in an atomic swap with a timelock of " + str(as_timelock_t) + " blocks? (y/n): ")
        if reply == "y":
            print()
            print("Initiating swap.")
            as_pubkey_sender_outgoing, as_pubkey_sender_incoming, as_pubkey_receiver_outgoing, as_pubkey_receiver_incoming = self.as_pubkey_exchange(as_wallet_receiver)
            return as_pubkey_sender_outgoing, as_pubkey_sender_incoming, as_pubkey_receiver_outgoing, as_pubkey_receiver_incoming
        elif reply == "n":
            print()
            print("Swap denied.")
            print()
            sys.exit(0)
        else:
            print()
            print("That is reply is invalid. Please enter 'y' or 'n'.")
            as_pubkey_sender_outgoing, as_pubkey_sender_incoming, as_pubkey_receiver_outgoing, as_pubkey_receiver_incoming = self.as_request(as_wallet_receiver, as_amount, as_timelock_t)
            return as_pubkey_sender_outgoing, as_pubkey_sender_incoming, as_pubkey_receiver_outgoing, as_pubkey_receiver_incoming


    # fake version
    def as_pubkey_exchange(self, as_wallet_receiver):
        as_pubkey_sender_outgoing = self.get_next_public_key().serialize()
        as_pubkey_sender_incoming = self.get_next_public_key().serialize()
        print()
        print("Here is my outgoing pubkey: " + str(as_pubkey_sender_outgoing))
        print()
        print("Here is my incoming pubkey: " + str(as_pubkey_sender_incoming))
        print()
        print("What is your pubkey?")
        # FIX THIS –– this is currently a placeholder for the pubkey received from the receiver
        as_pubkey_receiver_outgoing = as_wallet_receiver.get_next_public_key().serialize()
        as_pubkey_receiver_incoming = as_wallet_receiver.get_next_public_key().serialize()
        print()
        print("Your outgoing pubkey is: " + str(as_pubkey_receiver_outgoing))
        print()
        print("Your incoming pubkey is: " + str(as_pubkey_receiver_incoming))
        print()
        return as_pubkey_sender_outgoing, as_pubkey_sender_incoming, as_pubkey_receiver_outgoing, as_pubkey_receiver_incoming


    def as_generate_secret_hash(self, secret):
        secret_hash_cl = "(sha256 (q %s))" % (secret)
        sec = "(%s)" % secret
        secret_hash_preformat = clvm.eval_f(clvm.eval_f, binutils.assemble("(sha256 (f (a)))"), binutils.assemble(sec))
        secret_hash = binutils.disassemble(secret_hash_preformat)
        return secret_hash


    def as_make_puzzle(self, as_pubkey_sender, as_pubkey_receiver, as_amount, as_timelock_t, as_secret_hash):
        as_pubkey_sender_cl = "0x%s" % (hexlify(as_pubkey_sender).decode('ascii'))
        as_pubkey_receiver_cl = "0x%s" % (hexlify(as_pubkey_receiver).decode('ascii'))

        as_payout_puzzlehash_receiver = ProgramHash(puzzle_for_pk(as_pubkey_receiver))
        as_payout_puzzlehash_sender = ProgramHash(puzzle_for_pk(as_pubkey_sender))

        payout_receiver = "(c (q 0x%s) (c (q 0x%s) (c (q %d) (q ()))))" % (hexlify(ConditionOpcode.CREATE_COIN).decode('ascii'), hexlify(as_payout_puzzlehash_receiver).decode('ascii'), as_amount)
        payout_sender = "(c (q 0x%s) (c (q 0x%s) (c (q %d) (q ()))))" % (hexlify(ConditionOpcode.CREATE_COIN).decode('ascii'), hexlify(as_payout_puzzlehash_sender).decode('ascii'), as_amount)
        aggsig_receiver = "(c (q 0x%s) (c (q %s) (c (sha256 (wrap (a))) (q ()))))" % (hexlify(ConditionOpcode.AGG_SIG).decode('ascii'), as_pubkey_receiver_cl)
        aggsig_sender = "(c (q 0x%s) (c (q %s) (c (sha256 (wrap (a))) (q ()))))" % (hexlify(ConditionOpcode.AGG_SIG).decode('ascii'), as_pubkey_sender_cl)
        receiver_puz = ("(e (i (= (sha256 (f (r (a)))) (q %s)) (q (c " + aggsig_receiver + " (c " + payout_receiver + " (q ())))) (q (x (q 'invalid secret')))) (a)) ) ") % (as_secret_hash)
        timelock = "(c (q 0x%s) (c (q %d) (q ()))) " % (hexlify(ConditionOpcode.ASSERT_MIN_TIME).decode('ascii'), as_timelock_t)
        sender_puz = "(c " + aggsig_sender + " (c " + timelock + " (c " + payout_sender + " (q ()))))"
        as_puz_sender = "(e (i (= (f (a)) (q 77777)) (q " + sender_puz + ") (q (x (q 'not a valid option'))) ) (a))"
        as_puz = "(e (i (= (f (a)) (q 33333)) (q " + receiver_puz + " (q " + as_puz_sender + ")) (a))"
        return Program(binutils.assemble(as_puz))

        # 33333 is the receiver solution code prefix
        # 77777 is the sender solution code prefix
        # current version of the puzzle: (e (i (= (f (a)) (q 33333)) (q (e (i (= (sha256 (f (r (a)))) (q 30370204479623163331157306773352227112579049797730721831667874080735946490555)) (q (c (c (q 0x32) (c (q 0x83b1e2c1c70fae2c1a48c35962ec951d7e616b200ebf27afe961d1d9f21e9c6ef9db1280cc595704cfee57b8f9dcacdb) (c (sha256 (wrap (a))) (q ())))) (c (c (q 0x33) (c (q 0x6032796617db6a7b455b2527265387b04b0d46af519984955a8b193d99edc2ea) (c (q 100) (q ())))) (q ())))) (q (x (q 'invalid secret')))) (a)) )  (q (e (i (= (f (a)) (q 77777)) (q (c (c (q 0x32) (c (q 0x13369799f40d48d5cca6d9411e5240ef3ede5b89736d60515434d8f6a9d16afe1ca4f2a2bc05cf1d78e2a297ad278c5c) (c (sha256 (wrap (a))) (q ())))) (c (c (q 0x36) (c (q 5) (q ())))  (c (c (q 0x33) (c (q 0x4710364bfda779090f5dd9be860f040bf8ece778f862e596c6e1ef96d37bf605) (c (q 100) (q ())))) (q ()))))) (q (x (q 'not a valid option'))) ) (a)))) (a))
        # test receiver solution (successful): (33333 1234)
        # test receiver solution (fail): (33333 1235)
        # test sender solution: (77777)


    def as_get_new_puzzlehash(self, as_pubkey_sender, as_pubkey_receiver, as_amount, as_timelock_t, as_secret_hash):
        as_puz = self.as_make_puzzle(as_pubkey_sender, as_pubkey_receiver, as_amount, as_timelock_t, as_secret_hash)
        as_puzzlehash = ProgramHash(as_puz)
        return as_puzzlehash


    def as_make_solution_receiver(self, as_sec_to_try):
        sol = "(33333 "
        sol += "%s" % (as_sec_to_try)
        sol += ")"
        return Program(binutils.assemble(sol))


    def as_make_solution_sender(self):
        sol = "(77777 "
        sol += ")"
        return Program(binutils.assemble(sol))


    def get_private_keys(self):
        return [BLSPrivateKey(self.extended_secret_key.private_child(child).get_private_key()) for child in range(self.next_address)]


    def make_keychain(self):
        private_keys = self.get_private_keys()
        return dict((_.public_key(), _) for _ in private_keys)


    def make_signer(self):
        return sign_f_for_keychain(self.make_keychain())


    def as_create_spend_bundle(self, as_puzzlehash, as_amount, as_timelock_t, as_secret_hash, as_pubkey_sender = None, as_pubkey_receiver = None, who = None, as_sec_to_try = None):
        utxos = self.as_select_coins(as_amount, as_puzzlehash)
        spends = []
        for coin in utxos:
            puzzle = self.as_make_puzzle(as_pubkey_sender, as_pubkey_receiver, as_amount, as_timelock_t, as_secret_hash)
            if who == "sender":
                solution = self.as_make_solution_sender()
            elif who == "receiver":
                solution = self.as_make_solution_receiver(as_sec_to_try)
            pair = solution.code.to([puzzle.code, solution.code])
            signer = self.make_signer()
            spend_bundle = build_spend_bundle(coin, Program(pair), sign_f=signer)
            spends.append(spend_bundle)
        return SpendBundle.aggregate(spends)
