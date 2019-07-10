from enum import Enum


class ConsensusError(Exception, Enum):
    # temporary errors. Don't blacklist
    DOES_NOT_EXTEND = -1
    BAD_HEADER_SIGNATURE = -2
    MISSING_FROM_STORAGE = -3

    UNKNOWN = -9999

    # permanent errors. Block is unsalvageable garbage.
    BAD_COINBASE_SIGNATURE = 1
    INVALID_BLOCK_SOLUTION = 2
    DUPLICATE_OUTPUT = 3
    DOUBLE_SPEND = 4
    UNKNOWN_UNSPENT = 5
    BAD_AGGREGATE_SIGNATURE = 6
    WRONG_PUZZLE_HASH = 7
