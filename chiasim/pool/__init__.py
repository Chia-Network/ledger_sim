import blspy

from chiasim.atoms import uint64
from chiasim.hashable import std_hash, BLSSignature, Coin, Program


def make_coinbase_coin_and_signature(block_index: int, puzzle_program, pool_private_key, reward: uint64):
    puzzle_hash = std_hash(puzzle_program.as_bin())
    block_index_as_hash = block_index.to_bytes(32, "big")
    coin = Coin(block_index_as_hash, Program(puzzle_program), reward)
    message_hash = blspy.Util.hash256(coin.as_bin())
    sig = pool_private_key.sign_prepend_prehashed(message_hash)
    signature = BLSSignature(sig.serialize())
    return coin, signature

