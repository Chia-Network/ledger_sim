import blspy

from chiasim.hashable import ProgramHash
from chiasim.hashable import CoinSolution, SpendBundle

from chiasim.puzzles import p2_delegated_puzzle
from chiasim.validation.Conditions import (
    conditions_by_opcode, make_create_coin_condition
)
from chiasim.validation.consensus import (
    conditions_for_solution, hash_key_pairs_for_conditions_dict
)
from tests.BLSPrivateKey import BLSPrivateKey


HIERARCHICAL_PRIVATE_KEY = blspy.ExtendedPrivateKey.from_seed(b"foo")


def private_key_for_index(index):
    return HIERARCHICAL_PRIVATE_KEY.private_child(index).get_private_key()


def public_key_bytes_for_index(index):
    return HIERARCHICAL_PRIVATE_KEY.private_child(index).get_public_key().serialize()


def puzzle_program_for_index(index):
    return p2_delegated_puzzle.puzzle_for_pk(
        public_key_bytes_for_index(index))


def puzzle_hash_for_index(index):
    return ProgramHash(puzzle_program_for_index(index))


def conditions_for_payment(puzzle_hash_amount_pairs):
    conditions = [make_create_coin_condition(ph, amount) for ph, amount in puzzle_hash_amount_pairs]
    return conditions


def spend_coin(coin, conditions, index):
    solution = p2_delegated_puzzle.solution_for_conditions(
        puzzle_program_for_index(index), conditions)

    signatures = []
    conditions_dict = conditions_by_opcode(conditions_for_solution(solution.code))
    for _ in hash_key_pairs_for_conditions_dict(conditions_dict):
        bls_private_key = BLSPrivateKey(private_key_for_index(index))
        signature = bls_private_key.sign(_.message_hash)
        signatures.append(signature)

    signature = signatures[0].aggregate(signatures)
    coin_solution = CoinSolution(coin, solution)
    spend_bundle = SpendBundle([coin_solution], signature)
    return spend_bundle
