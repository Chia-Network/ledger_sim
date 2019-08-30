import hashlib
import clvm
from os import urandom
from blspy import ExtendedPrivateKey
from chiasim.puzzles.p2_delegated_puzzle import puzzle_for_pk
from chiasim.hashable import Program, ProgramHash, CoinSolution, SpendBundle, BLSSignature
from chiasim.hashable.CoinSolution import CoinSolutionList
from chiasim.puzzles.p2_conditions import puzzle_for_conditions
from chiasim.validation.Conditions import (
    conditions_by_opcode, make_create_coin_condition, make_assert_my_coin_id_condition, make_assert_min_time_condition
)
from chiasim.validation.consensus import (
    conditions_for_solution, hash_key_pairs_for_conditions_dict
)
from .BLSPrivateKey import BLSPrivateKey


def sha256(val):
    return hashlib.sha256(val).digest()


def make_solution(primaries=[], min_time=0, me={}):
    ret = []
    for primary in primaries:
        ret.append(make_create_coin_condition(primary['puzzlehash'], primary['amount']))
    if min_time > 0:
        ret.append(make_assert_min_time_condition(min_time))
    if me:
        ret.append(make_assert_my_coin_id_condition(me['id']))
    return puzzle_for_conditions(ret)


class Wallet:
    seed = b'seed'
    next_address = 0
    pubkey_num_lookup = {}

    def __init__(self):
        self.current_balance = 0
        self.my_utxos = set()
        self.seed = urandom(1024)
        self.extended_secret_key = ExtendedPrivateKey.from_seed(self.seed)

    def get_next_public_key(self):
        pubkey = self.extended_secret_key.public_child(self.next_address).get_public_key()
        self.pubkey_num_lookup[pubkey.serialize()] = self.next_address
        self.next_address = self.next_address + 1
        return pubkey

    def can_generate_puzzle_hash(self, hash):
        return any(map(lambda child: hash == ProgramHash(puzzle_for_pk(
            self.extended_secret_key.public_child(child).get_public_key().serialize())),
                reversed(range(self.next_address))))

    def get_keys(self, hash):
        for child in range(self.next_address):
            pubkey = self.extended_secret_key.public_child(child).get_public_key()
            if hash == ProgramHash(puzzle_for_pk(pubkey.serialize())):
                return (pubkey, self.extended_secret_key.private_child(child).get_private_key())

    def notify(self, additions, deletions):
        for coin in deletions:
            if coin in self.my_utxos:
                self.my_utxos.remove(coin)
                self.current_balance -= coin.amount
        for coin in additions:
            if self.can_generate_puzzle_hash(coin.puzzle_hash):
                self.current_balance += coin.amount
                self.my_utxos.add(coin)

    def select_coins(self, amount):
        if amount > self.current_balance:
            return None

        used_utxos = set()
        coins = self.my_utxos.copy()
        while sum(map(lambda coin: coin.amount, used_utxos)) < amount:
            used_utxos.add(coins.pop())
        return used_utxos

    def get_new_puzzle(self):
        pubkey = self.get_next_public_key().serialize()
        puzzle = puzzle_for_pk(pubkey)
        return puzzle

    def get_new_puzzlehash(self):
        puzzle = self.get_new_puzzle()
        puzzlehash = ProgramHash(puzzle)
        return puzzlehash

    def sign(self, value, pubkey = None):
        if pubkey is not None:
            privatekey = self.extended_secret_key.private_child(self.pubkey_num_lookup[pubkey]).get_private_key()
        else:
            pubkey = self.extended_secret_key.public_child(self.next_address).get_public_key()
            privatekey = self.extended_secret_key.private_child(self.next_address).get_private_key()
            self.pubkey_num_lookup[pubkey.serialize()] = self.next_address
            self.next_address = self.next_address + 1
        blskey = BLSPrivateKey(privatekey)
        return blskey.sign(value)

    # returns {'spends' spends, 'signature': None}
    # spends is {(primary_input, puzzle): solution}
    def generate_unsigned_transaction(self, amount, newpuzzlehash, utxoset):
        utxos = self.select_coins(amount)
        spends = {}
        output_id = None
        spend_value = sum([utxoset[id]['value'] for id in utxos])
        change = spend_value - amount
        for id in utxos:
            primary = utxoset[id]['primary']
            puzzle_hash = utxoset[id]['puzzlehash']
            pubkey, secretkey = self.get_keys(puzzle_hash)
            puzzle = puzzle_for_pk(pubkey.serialize())
            if output_id == None:
                primaries = [{'puzzlehash': newpuzzlehash, 'amount': amount}]
                if change > 0:
                    changepuzzlehash = self.get_new_puzzlehash()
                    primaries.append({'puzzlehash': changepuzzlehash, 'amount': change})
                solution = make_solution(primaries=primaries)
                output_id = sha256(id + newpuzzlehash)
            else:
                solution = make_solution(outputs=[{'id': output_id, 'amount': amount}])

            spends[(primary, puzzle)] = solution

        unsigned_transaction = {'spends': spends, 'signature': None}
        return unsigned_transaction

    def generate_unsigned_transaction(self, amount, newpuzzlehash):
        utxos = self.select_coins(amount)
        spends = []
        output_id = None
        spend_value = sum([coin.amount for coin in utxos])
        change = spend_value - amount
        for coin in utxos:
            puzzle_hash = coin.puzzle_hash

            pubkey, secretkey = self.get_keys(puzzle_hash)
            puzzle = puzzle_for_pk(pubkey.serialize())
            if output_id == None:
                primaries = [{'puzzlehash': newpuzzlehash, 'amount': amount}]
                if change > 0:
                    changepuzzlehash = self.get_new_puzzlehash()
                    primaries.append({'puzzlehash': changepuzzlehash, 'amount': change})
                solution = make_solution(primaries=primaries)
                output_id = sha256(coin.name() + newpuzzlehash)
            else:
                solution = make_solution()
            spends.append((puzzle, CoinSolution(coin, solution)))
        return spends

    def sign_transaction(self, spends: (Program, [CoinSolution])):
        sigs = []
        for puzzle, solution in spends:
            pubkey, secretkey = self.get_keys(solution.coin.puzzle_hash)
            secretkey = BLSPrivateKey(secretkey)
            code_ = [puzzle.code, [solution.solution.code, []]]
            sexp = clvm.to_sexp_f(code_)
            conditions_dict = conditions_by_opcode(conditions_for_solution(sexp))
            for _ in hash_key_pairs_for_conditions_dict(conditions_dict):
                signature = secretkey.sign(_.message_hash)
                sigs.append(signature)
        aggsig = BLSSignature.aggregate(sigs)
        solution_list = CoinSolutionList(
            [CoinSolution(coin_solution.coin, clvm.to_sexp_f([puzzle.code, [coin_solution.solution.code, []]])) for
             (puzzle, coin_solution) in spends])
        spend_bundle = SpendBundle(solution_list, aggsig)
        return spend_bundle

    def generate_signed_transaction(self, amount, newpuzzlehash):
        transaction = self.generate_unsigned_transaction(amount, newpuzzlehash)
        return self.sign_transaction(transaction)
