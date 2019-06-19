from ..atoms import uint32, uint64, streamable


@streamable
class Unspent:
    amount: uint64
    confirmed_block_index: uint32
    spent_block_index: uint32
