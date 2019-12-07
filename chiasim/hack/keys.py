from chiasim.hashable import CoinSolution, ProgramHash, SpendBundle
from chiasim.puzzles import p2_delegated_puzzle
from chiasim.validation.Conditions import make_create_coin_condition
from chiasim.wallet.BLSHDKey import BLSPrivateHDKey
from chiasim.wallet.keychain import Keychain


HIERARCHICAL_PRIVATE_KEY = BLSPrivateHDKey.from_seed(b"foo")


def secret_exponent_for_index(index):
    return HIERARCHICAL_PRIVATE_KEY.secret_exponent_for_child(index)


def public_key_bytes_for_index(index):
    return HIERARCHICAL_PRIVATE_KEY.public_child(index)


def puzzle_program_for_index(index):
    return p2_delegated_puzzle.puzzle_for_pk(public_key_bytes_for_index(index))


def puzzle_hash_for_index(index):
    return ProgramHash(puzzle_program_for_index(index))


def conditions_for_payment(puzzle_hash_amount_pairs):
    conditions = [
        make_create_coin_condition(ph, amount)
        for ph, amount in puzzle_hash_amount_pairs
    ]
    return conditions


def make_default_keychain():
    keychain = Keychain()
    secret_exponents = [secret_exponent_for_index(_) for _ in range(10)]
    keychain.add_secret_exponents(secret_exponents)
    return keychain


DEFAULT_KEYCHAIN = make_default_keychain()


def spend_coin(coin, conditions, index, keychain=DEFAULT_KEYCHAIN):
    solution = p2_delegated_puzzle.solution_for_conditions(
        puzzle_program_for_index(index), conditions
    )
    return build_spend_bundle(coin, solution, keychain)


def build_spend_bundle(coin, solution, keychain=DEFAULT_KEYCHAIN):
    coin_solution = CoinSolution(coin, solution)
    signature = keychain.signature_for_solution(solution)
    return SpendBundle([coin_solution], signature)
