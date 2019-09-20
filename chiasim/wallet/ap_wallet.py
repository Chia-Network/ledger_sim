from chiasim.wallet.wallet import Wallet
import hashlib
import clvm
from chiasim.hashable import Program, ProgramHash, CoinSolution, SpendBundle, BLSSignature
from binascii import hexlify
from chiasim.hashable.Coin import Coin
from chiasim.hashable.CoinSolution import CoinSolutionList
from clvm_tools import binutils
from .BLSPrivateKey import BLSPrivateKey
from blspy import PublicKey
from chiasim.validation.Conditions import ConditionOpcode
from chiasim.puzzles.p2_delegated_puzzle import puzzle_for_pk
from chiasim.puzzles.puzzle_utilities import pubkey_format, puzzlehash_from_string


def sha256(val):
    return hashlib.sha256(val).digest()


def serialize(myobject):
    return bytes(myobject, 'utf-8')


class APWallet(Wallet):
    def __init__(self):
        super().__init__()
        self.aggregation_coins = set()
        self.a_pubkey = None
        self.AP_puzzlehash = None
        self.approved_change_puzzle = None
        self.approved_change_signature = None
        self.temp_coin = None
        self.temp_coin_flag = False
        return

    def set_sender_values(self, AP_puzzlehash, a_pubkey_used):
        if isinstance(AP_puzzlehash, str):
            self.AP_puzzlehash = puzzlehash_from_string(AP_puzzlehash)
        else:
            self.AP_puzzlehash = AP_puzzlehash

        if isinstance(a_pubkey_used, str):
            a_pubkey = PublicKey.from_bytes(bytes.fromhex(a_pubkey_used))
            self.a_pubkey = a_pubkey
        else:
            self.a_pubkey = a_pubkey_used

    def set_approved_change_signature(self, signature):
        self.approved_change_signature = signature

    # allows wallet A to generate and sign permitted puzzlehashes ahead of time
    # returns a tuple of (puzhash, signature)
    def ap_generate_signatures(self, puzhashes, oldpuzzlehash, b_pubkey_used):
        puzhash_signature_list = []
        pubkey, secretkey = self.get_keys(oldpuzzlehash, None, b_pubkey_used)
        blskey = BLSPrivateKey(secretkey)
        signature = blskey.sign(oldpuzzlehash)
        puzhash_signature_list.append((oldpuzzlehash, signature))
        for p in puzhashes:
            signature = blskey.sign(p)
            puzhash_signature_list.append((p, signature))

        return puzhash_signature_list

    # pass in a_pubkey if you want the AP mode
    def get_keys(self, hash, a_pubkey_used=None, b_pubkey_used=None):
        for child in reversed(range(self.next_address)):
            pubkey = self.extended_secret_key.public_child(
                child).get_public_key()
            if hash == ProgramHash(puzzle_for_pk(pubkey.serialize())):
                return (pubkey, self.extended_secret_key.private_child(child).get_private_key())
            if a_pubkey_used is not None and b_pubkey_used is None:
                if hash == ProgramHash(self.ap_make_puzzle(a_pubkey_used, pubkey.serialize())):
                    return (pubkey, self.extended_secret_key.private_child(child).get_private_key())
            elif a_pubkey_used is None and b_pubkey_used is not None:
                if hash == ProgramHash(self.ap_make_puzzle(pubkey.serialize(), b_pubkey_used)):
                    return (pubkey, self.extended_secret_key.private_child(child).get_private_key())

    def notify(self, additions, deletions):
        super().notify(additions, deletions)
        self.ap_notify(additions)
        spend_bundle_list = self.ac_notify(additions)
        return spend_bundle_list

    def ap_notify(self, additions):
        # this prevents unnecessary checks
        if self.AP_puzzlehash is not None and not self.my_utxos:
            for coin in additions:
                if coin.puzzle_hash == self.AP_puzzlehash:
                    self.puzzle_generator = "(q (c (c (q 0x35) (c (f (a)) (q ()))) (c (c (q 0x34) (c (sha256 (sha256 (f (r (a))) (q 0xd372eab077f8d4923ef663b013ec0a4d2b53552beecd0c32fdede92bee89c1fe) (uint64 (f (r (r (a)))))) (sha256 (wrap (c (q 7) (c (c (q 5) (c (c (q 1) (c (f (a)) (q ()))) (c (q (q ())) (q ())))) (q ()))))) (uint64 (q 0))) (q ()))) (q ()))))"
                    self.puzzle_generator_id = str(ProgramHash(Program(binutils.assemble(self.puzzle_generator))))
                    self.current_balance += coin.amount
                    self.my_utxos.add(coin)
                    print("this coin is locked using my ID, it's output must be for me")

    # same notes as above but for aggregation coins
    def ac_notify(self, additions):
        if self.my_utxos:
            self.temp_coin = self.my_utxos.copy().pop()
        spend_bundle_list = []

        for coin in additions:
            if self.temp_coin_flag:
                my_utxos_copy = self.my_utxos.copy()
                for mycoin in self.my_utxos:
                    if coin.parent_coin_info == mycoin.name():
                        my_utxos_copy.remove(mycoin)
                        self.current_balance -= mycoin.amount
                self.my_utxos = my_utxos_copy

            for mycoin in self.my_utxos:
                if ProgramHash(self.ap_make_aggregation_puzzle(mycoin.puzzle_hash)) == coin.puzzle_hash:
                    self.aggregation_coins.add(coin)
                    spend_bundle = self.ap_generate_signed_aggregation_transaction()
                    spend_bundle_list.append(spend_bundle)

        if len(spend_bundle_list) > 1:
            self.temp_coin_flag = True
        else:
            self.temp_coin_flag = False

        if spend_bundle_list:
            return spend_bundle_list
        else:
            return None

    # this function generates ChiaScript that will merge two lists

    def merge_two_lists(self, list1=None, list2=None):
        if (list1 is None) or (list2 is None):
            return None
        ret = "(e (q (e (f (a)) (a))) (c (q (e (i (e (i (f (r (a))) (q (q ())) (q (q 1))) (a)) (q (f (c (f (r (r (a)))) (q ())))) (q (e (f (a)) (c (f (a)) (c (r (f (r (a)))) (c (c (f (f (r (a)))) (f (r (r (a))))) (q ()))))))) (a))) (c " + list1 + " (c " + list2 + " (q ())))))"
        return ret

    # this creates our authorised payee puzzle
    def ap_make_puzzle(self, a_pubkey_serialized, b_pubkey_serialized):
        a_pubkey = pubkey_format(a_pubkey_serialized)
        b_pubkey = pubkey_format(b_pubkey_serialized)

        # Mode one is for spending to one of the approved destinations
        # Solution contains (option 1 flag, list of (output puzzle hash (C/D), amount), my_primary_input, wallet_puzzle_hash)
        sum_outputs = "(e (q (e (f (a)) (a))) (c (q (e (i (e (i (f (r (a))) (q (q ())) (q (q 1))) (a)) (q (q 0)) (q (+ (f (r (f (f (r (a)))))) (e (f (a)) (c (f (a)) (c (r (f (r (a)))) (q ()))))))) (a))) (c (f (r (a))) (q ()))))"
        mode_one_me_string = "(c (q 0x%s) (c (sha256 (f (r (r (a)))) (f (r (r (r (a))))) (uint64 %s)) (q ())))" % (
            hexlify(ConditionOpcode.ASSERT_MY_COIN_ID).decode('ascii'), sum_outputs)
        aggsig_outputs = "(e (q (e (f (a)) (a))) (c (q (e (i (e (i (f (r (a))) (q (q ())) (q (q 1))) (a)) (q (q ())) (q (c (c (q 0x%s) (c (q %s) (c (f (f (f (r (a))))) (q ())))) (e (f (a)) (c (f (a)) (c (r (f (r (a)))) (q ()))))))) (a))) (c (f (r (a))) (q ()))))" % (
            hexlify(ConditionOpcode.AGG_SIG).decode('ascii'), a_pubkey)
        aggsig_entire_solution = "(c (q 0x%s) (c (q %s) (c (sha256 (wrap (a))) (q ()))))" % (
            hexlify(ConditionOpcode.AGG_SIG).decode('ascii'), b_pubkey)
        create_outputs = "(e (q (e (f (a)) (a))) (c (q (e (i (e (i (f (r (a))) (q (q ())) (q (q 1))) (a)) (q (q ())) (q (c (c (q 0x%s) (c (f (f (f (r (a))))) (c (f (r (f (f (r (a)))))) (q ())))) (e (f (a)) (c (f (a)) (c (r (f (r (a)))) (q ()))))))) (a))) (c (f (r (a))) (q ()))))" % (
            hexlify(ConditionOpcode.CREATE_COIN).decode('ascii'))
        mode_one = "(c " + aggsig_entire_solution + \
            " (c " + mode_one_me_string + " " + aggsig_outputs + "))"
        mode_one = self.merge_two_lists(create_outputs, mode_one)

        # Mode two is for aggregating in another coin and expanding our single coin wallet
        # Solution contains (option 2 flag, wallet_puzzle_hash, consolidating_coin_primary_input, consolidating_coin_puzzle_hash, consolidating_coin_amount, my_primary_input, my_amount)
        create_consolidated = '(c (q 0x%s) (c (f (r (a))) (c (+ (f (r (r (r (r (a)))))) (f (r (r (r (r (r (r (a))))))))) (q ()))))' % hexlify(
            ConditionOpcode.CREATE_COIN).decode('ascii')
        mode_two_me_string = "(c (q 0x%s) (c (sha256 (f (r (r (r (r (r (a))))))) (f (r (a))) (uint64 (f (r (r (r (r (r (r (a)))))))))) (q ())))" % (
            hexlify(ConditionOpcode.ASSERT_MY_COIN_ID).decode('ascii'))
        create_lock = "(c (q 0x%s) (c (sha256 (wrap (c (q 7) (c (c (q 5) (c (c (q 1) (c (sha256 (f (r (r (a)))) (f (r (r (r (a))))) (uint64 (f (r (r (r (r (a)))))))) (q ()))) (c (q (q ())) (q ())))) (q ()))))) (c (uint64 (q 0)) (q ()))))" % hexlify(
            ConditionOpcode.CREATE_COIN).decode('ascii')
        mode_two = '(c ' + mode_two_me_string + ' (c ' + aggsig_entire_solution + \
            ' (c ' + create_lock + ' (c ' + create_consolidated + ' (q ())))))'

        puz = "(e (i (= (f (a)) (q 1)) (q " + mode_one + ") (q " + mode_two + ")) (a))"
        # temporary - will eventually be puz
        return Program(binutils.assemble(puz))

    def ap_make_aggregation_puzzle(self, wallet_puzzle):
        # If Wallet A wants to send further funds to Wallet B then they can lock them up using this code
        # Solution will be (my_id wallet_coin_primary_input wallet_coin_amount)
        me_is_my_id = '(c (q 0x%s) (c (f (a)) (q ())))' % (
            hexlify(ConditionOpcode.ASSERT_MY_COIN_ID).decode('ascii'))
        # lock_puzzle is the hash of '(r (c (q "merge in ID") (q ())))'
        lock_puzzle = '(sha256 (wrap (c (q 7) (c (c (q 5) (c (c (q 1) (c (f (a)) (q ()))) (c (q (q ())) (q ())))) (q ())))))'
        parent_coin_id = "(sha256 (f (r (a))) (q 0x%s) (uint64 (f (r (r (a))))))" % hexlify(
            wallet_puzzle).decode('ascii')
        input_of_lock = '(c (q 0x%s) (c (sha256 %s %s (uint64 (q 0))) (q ())))' % (hexlify(
            ConditionOpcode.ASSERT_COIN_CONSUMED).decode('ascii'), parent_coin_id, lock_puzzle)
        puz = '(c ' + me_is_my_id + ' (c ' + input_of_lock + ' (q ())))'
        print(puz)
        return Program(binutils.assemble(puz))

    # returns the ProgramHash of a new puzzle
    def ap_get_new_puzzlehash(self, a_pubkey_serialized, b_pubkey_serialized):
        return ProgramHash(self.ap_make_puzzle(a_pubkey_serialized, b_pubkey_serialized))

    def ap_get_aggregation_puzzlehash(self, wallet_puzzle):
        return ProgramHash(self.ap_make_aggregation_puzzle(wallet_puzzle))

    # creates the solution that will allow wallet B to spend the coin
    # Wallet B is allowed to make multiple spends but must spend the coin in its entirety
    def ap_make_solution_mode_1(self, outputs=[], my_primary_input=0x0000, my_puzzle_hash=0x0000):
        sol = "(1 ("
        for puzhash, amount in outputs:
            sol += "(0x%s %d)" % (hexlify(puzhash).decode('ascii'), amount)
        sol += ") "
        sol += "0x%s " % (hexlify(my_primary_input).decode('ascii'))
        sol += "0x%s" % (hexlify(my_puzzle_hash).decode('ascii'))
        sol += ")"
        return Program(binutils.assemble(sol))

    def ac_make_aggregation_solution(self, myid, wallet_coin_primary_input, wallet_coin_amount):
        sol = "(0x%s 0x%s %d)" % (hexlify(myid).decode('ascii'), hexlify(
            wallet_coin_primary_input).decode('ascii'), wallet_coin_amount)
        return Program(binutils.assemble(sol))

    def ap_make_solution_mode_2(self, wallet_puzzle_hash, consolidating_primary_input, consolidating_coin_puzzle_hash, outgoing_amount, my_primary_input, incoming_amount):
        sol = "(2 0x%s 0x%s 0x%s %d 0x%s %d)" % (hexlify(wallet_puzzle_hash).decode('ascii'), hexlify(consolidating_primary_input).decode(
            'ascii'), hexlify(consolidating_coin_puzzle_hash).decode('ascii'), outgoing_amount, hexlify(my_primary_input).decode('ascii'), incoming_amount)
        return Program(binutils.assemble(sol))

    # this is for sending a recieved ap coin, not creating a new ap coin
    def ap_generate_unsigned_transaction(self, puzzlehash_amount_list):
        # we only have/need one coin in this wallet at any time - this code can be improved
        utxos = self.select_coins(self.current_balance)
        spends = []
        coin = self.temp_coin
        puzzle_hash = coin.puzzle_hash

        pubkey, secretkey = self.get_keys(puzzle_hash, self.a_pubkey)
        puzzle = self.ap_make_puzzle(self.a_pubkey, pubkey.serialize())
        solution = self.ap_make_solution_mode_1(
            puzzlehash_amount_list, coin.parent_coin_info, puzzle_hash)
        spends.append((puzzle, CoinSolution(coin, solution)))
        return spends

    # this allows wallet A to approve of new puzzlehashes/spends from wallet B that weren't in the original list
    def ap_sign_output_newpuzzlehash(self, puzzlehash, newpuzzlehash, b_pubkey_used):
        pubkey, secretkey = self.get_keys(puzzlehash, None, b_pubkey_used)
        signature = BLSPrivateKey(secretkey).sign(newpuzzlehash)
        return signature

    # this is for sending a locked coin
    # Wallet B must sign the whole transaction, and the appropriate puzhash signature from A must be included
    def ap_sign_transaction(self, spends: (Program, [CoinSolution]), signatures_from_a):
        sigs = []
        for puzzle, solution in spends:
            pubkey, secretkey = self.get_keys(
                solution.coin.puzzle_hash, self.a_pubkey)
            secretkey = BLSPrivateKey(secretkey)
            signature = secretkey.sign(
                ProgramHash(Program(solution.solution.code)))
            sigs.append(signature)
        for s in signatures_from_a:
            sigs.append(s)
        aggsig = BLSSignature.aggregate(sigs)
        solution_list = CoinSolutionList(
            [CoinSolution(coin_solution.coin, clvm.to_sexp_f([puzzle.code, coin_solution.solution.code])) for
             (puzzle, coin_solution) in spends])
        spend_bundle = SpendBundle(solution_list, aggsig)
        breakpoint()
        return spend_bundle

    # this is for sending a recieved ap coin, not sending a new ap coin
    def ap_generate_signed_transaction(self, puzzlehash_amount_list, signatures_from_a):
        # calculate change
        spend_value = 0
        for puzzlehash, amount in puzzlehash_amount_list:
            spend_value += amount
        change = self.current_balance - spend_value
        puzzlehash_amount_list.append((self.AP_puzzlehash, change))
        signatures_from_a.append(self.approved_change_signature)
        breakpoint()
        transaction = self.ap_generate_unsigned_transaction(
            puzzlehash_amount_list)
        breakpoint()
        return self.ap_sign_transaction(transaction, signatures_from_a)

    # This is for using the AC locked coin and aggregating it into wallet - must happen in same block as AP Mode 2
    def ap_generate_signed_aggregation_transaction(self):
        list_of_coinsolutions = []
        if self.aggregation_coins is False:  # empty sets evaluate to false in python
            return
        consolidating_coin = self.aggregation_coins.pop()

        pubkey, secretkey = self.get_keys(
            self.temp_coin.puzzle_hash, self.a_pubkey)

        # Spend wallet coin
        puzzle = self.ap_make_puzzle(self.a_pubkey, pubkey.serialize())
        solution = self.ap_make_solution_mode_2(self.temp_coin.puzzle_hash, consolidating_coin.parent_coin_info,
                                                consolidating_coin.puzzle_hash, consolidating_coin.amount, self.temp_coin.parent_coin_info, self.temp_coin.amount)
        signature = BLSPrivateKey(secretkey).sign(ProgramHash(solution))
        list_of_coinsolutions.append(CoinSolution(
            self.temp_coin, clvm.to_sexp_f([puzzle.code, solution.code])))

        # Spend consolidating coin
        puzzle = self.ap_make_aggregation_puzzle(self.temp_coin.puzzle_hash)
        solution = self.ac_make_aggregation_solution(consolidating_coin.name(
        ), self.temp_coin.parent_coin_info, self.temp_coin.amount)
        list_of_coinsolutions.append(CoinSolution(
            consolidating_coin, clvm.to_sexp_f([puzzle.code, solution.code])))

        # Spend lock
        puzstring = "(r (c (q 0x" + hexlify(consolidating_coin.name()
                                            ).decode('ascii') + ") (q ())))"
        puzzle = Program(binutils.assemble(puzstring))
        solution = Program(binutils.assemble("()"))
        list_of_coinsolutions.append(CoinSolution(Coin(self.temp_coin, ProgramHash(
            puzzle), 0), clvm.to_sexp_f([puzzle.code, solution.code])))

        self.temp_coin = Coin(self.temp_coin, self.temp_coin.puzzle_hash,
                              self.temp_coin.amount + consolidating_coin.amount)
        aggsig = BLSSignature.aggregate([signature])
        solution_list = CoinSolutionList(list_of_coinsolutions)
        return SpendBundle(solution_list, aggsig)
