from chiasim.hashable import std_hash
from chiasim.puzzles import p2_delegated_puzzle
from chiasim.validation.consensus import (
    conditions_for_solution, created_outputs_for_conditions_dict
)
from chiasim.validation.Conditions import conditions_by_opcode, make_create_coin_condition

from tests.helpers import (
    PUBLIC_KEYS,
    trace_eval,
)


def test_1():
    pub_key_0, pub_key_1, pub_key_2 = PUBLIC_KEYS[:3]

    puzzle_program_0 = p2_delegated_puzzle.puzzle_for_pk(pub_key_0)
    puzzle_program_1 = p2_delegated_puzzle.puzzle_for_pk(pub_key_1)
    puzzle_program_2 = p2_delegated_puzzle.puzzle_for_pk(pub_key_2)

    conditions = [make_create_coin_condition(std_hash(pp.as_bin()), amount) for pp, amount in [
        (puzzle_program_1, 1000), (puzzle_program_2, 2000),
    ]]

    puzzle_hash_solution = p2_delegated_puzzle.solution_for_conditions(puzzle_program_0, conditions)

    output_conditions = conditions_for_solution(puzzle_hash_solution.code, trace_eval)
    from pprint import pprint
    output_conditions_dict = conditions_by_opcode(output_conditions)
    pprint(output_conditions_dict)
    input_coin_info_hash = bytes([0] * 32)
    additions = created_outputs_for_conditions_dict(output_conditions_dict, input_coin_info_hash)
    print(additions)
    assert len(additions) == 2
