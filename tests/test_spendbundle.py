from chiasim.hashable import std_hash
from chiasim.validation.consensus import conditions_for_puzzle_hash_solution, created_outputs_for_conditions_dict
from chiasim.validation.Conditions import conditions_by_opcode, make_create_coin_condition

from tests.helpers import (
    make_simple_puzzle_program,
    make_solution_to_simple_puzzle_program,
    PUBLIC_KEYS,
    trace_eval,
)


def test_1():
    pub_key_0, pub_key_1, pub_key_2 = PUBLIC_KEYS[:3]

    puzzle_program_0 = make_simple_puzzle_program(pub_key_0)
    puzzle_program_1 = make_simple_puzzle_program(pub_key_1)
    puzzle_program_2 = make_simple_puzzle_program(pub_key_2)

    conditions = [make_create_coin_condition(std_hash(pp.as_bin()), amount) for pp, amount in [
        (puzzle_program_1, 1000), (puzzle_program_2, 2000),
    ]]

    puzzle_hash_solution_blob = make_solution_to_simple_puzzle_program(puzzle_program_0, conditions)

    puzzle_hash = std_hash(puzzle_program_0.as_bin())

    output_conditions = conditions_for_puzzle_hash_solution(
        puzzle_hash, puzzle_hash_solution_blob, trace_eval)
    from pprint import pprint
    output_conditions_dict = conditions_by_opcode(output_conditions)
    pprint(output_conditions_dict)
    input_coin_info_hash = bytes([0] * 32)
    additions = created_outputs_for_conditions_dict(output_conditions_dict, input_coin_info_hash)
    print(additions)
    assert len(additions) == 2
