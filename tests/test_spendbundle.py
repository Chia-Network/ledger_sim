from chiasim.hack.keys import puzzle_program_for_index
from chiasim.hashable import std_hash
from chiasim.puzzles import p2_delegated_puzzle
from chiasim.validation.consensus import (
    conditions_for_solution, created_outputs_for_conditions_dict
)
from chiasim.validation.Conditions import conditions_by_opcode, make_create_coin_condition

from .helpers import trace_eval


def test_1():
    puzzle_program_0 = puzzle_program_for_index(0)
    puzzle_program_1 = puzzle_program_for_index(1)
    puzzle_program_2 = puzzle_program_for_index(2)

    conditions = [make_create_coin_condition(std_hash(bytes(pp)), amount) for pp, amount in [
        (puzzle_program_1, 1000), (puzzle_program_2, 2000),
    ]]

    puzzle_hash_solution = p2_delegated_puzzle.solution_for_conditions(puzzle_program_0, conditions)

    output_conditions = conditions_for_solution(puzzle_hash_solution, trace_eval)
    from pprint import pprint
    output_conditions_dict = conditions_by_opcode(output_conditions)
    pprint(output_conditions_dict)
    input_coin_info_hash = bytes([0] * 32)
    additions = created_outputs_for_conditions_dict(output_conditions_dict, input_coin_info_hash)
    print(additions)
    assert len(additions) == 2
