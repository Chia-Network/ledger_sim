import asyncio
import blspy

from chiasim.atoms import uint64
from chiasim.farming import Mempool
from chiasim.hashable import (
    std_hash, Coin, EORPrivateKey,
    ProofOfSpace, BLSSignature, BLSPublicKey
)
from chiasim.storage import RAM_DB

from .helpers import build_spend_bundle, make_simple_puzzle_program, PRIVATE_KEYS, PUBLIC_KEYS


# pool manager function
def make_coinbase_coin_and_signature(block_index, puzzle_program, pool_private_key=PRIVATE_KEYS[0]):
    puzzle_hash = std_hash(puzzle_program.as_bin())
    block_index_as_hash = block_index.to_bytes(32, "big")
    coin = Coin(block_index_as_hash, puzzle_hash, uint64(10000))
    message_hash = blspy.Util.hash256(coin.as_bin())
    sig = pool_private_key.sign_prepend_prehashed(message_hash)
    signature = BLSSignature(sig.serialize())
    return coin, signature


def fake_hash(v):
    return std_hash(bytes([v]))


def fake_plot_private_key():
    return EORPrivateKey(fake_hash(4))


def fake_proof_of_space(plot_public_key=None, pool_public_key=None):
    # TODO: fix this
    if plot_public_key is None:
        plot_private_key = fake_plot_private_key()
        plot_public_key = plot_private_key.public_key()

    if pool_public_key is None:
        pool_public_key = BLSPublicKey.from_bin(PRIVATE_KEYS[0].get_public_key().serialize())

    return ProofOfSpace(pool_public_key, plot_public_key)


def farm_block(mempool, block_number, proof_of_space, coinbase_coin, coinbase_signature, plot_private_key):
    # TODO: fix this
    fees_puzzle_hash = fake_hash(100)

    header, body, additions, removals = mempool.farm_new_block(
        block_number, proof_of_space, coinbase_coin, coinbase_signature, fees_puzzle_hash)

    header_signature = plot_private_key.sign(header.hash())

    bad_bls_public_key = BLSPublicKey.from_bin(PRIVATE_KEYS[9].get_public_key().serialize())

    bad_eor_public_key = EORPrivateKey(fake_hash(5)).public_key()

    hkp = header_signature.aggsig_pair(proof_of_space.plot_public_key, header.hash())
    _ = header_signature.validate([hkp])
    assert _

    hkp = header_signature.aggsig_pair(bad_eor_public_key, header.hash())
    assert not header_signature.validate([hkp])

    hkp = body.coinbase_signature.aggsig_pair(proof_of_space.pool_public_key, body.coinbase_coin.hash())
    assert body.coinbase_signature.validate([hkp])

    hkp = body.coinbase_signature.aggsig_pair(bad_bls_public_key, body.coinbase_coin.hash())
    assert not body.coinbase_signature.validate([hkp])
    return header, header_signature


def test_farm_block_empty():
    # TODO: fix
    db = RAM_DB()
    FIRST_BLOCK = fake_hash(0)

    mempool = Mempool(FIRST_BLOCK, db)
    mempool.minimum_legal_timestamp = lambda: int(1e10)

    pos = fake_proof_of_space()

    pool_private_key = PRIVATE_KEYS[0]

    puzzle_program = make_simple_puzzle_program(PUBLIC_KEYS[1])
    coinbase_coin, coinbase_signature = make_coinbase_coin_and_signature(
        1, puzzle_program, pool_private_key)

    plot_private_key = fake_plot_private_key()
    header, header_signature = farm_block(
        mempool, 1, pos, coinbase_coin, coinbase_signature, plot_private_key)


def test_farm_block_one_spendbundle():
    db = RAM_DB()
    FIRST_BLOCK = fake_hash(0)

    mempool = Mempool(FIRST_BLOCK, db)
    mempool.minimum_legal_timestamp = lambda: int(1e10)

    spend_bundle = build_spend_bundle()
    mempool.accept_spend_bundle(spend_bundle)

    pos = fake_proof_of_space()

    pool_private_key = PRIVATE_KEYS[0]

    puzzle_program = make_simple_puzzle_program(PUBLIC_KEYS[1])
    coinbase_coin, coinbase_signature = make_coinbase_coin_and_signature(
        1, puzzle_program, pool_private_key)

    plot_private_key = fake_plot_private_key()
    header, header_signature = farm_block(
        mempool, 2, pos, coinbase_coin, coinbase_signature, plot_private_key)


def test_farm_two_blocks():
    """
    In this test, we farm two blocks: one empty block,
    then one block which spends the coinbase transaction from the empty block.
    """
    db = RAM_DB()
    FIRST_BLOCK = fake_hash(0)

    mempool = Mempool(FIRST_BLOCK, db)
    mempool.minimum_legal_timestamp = lambda: int(1e10)
    pos_1 = fake_proof_of_space()

    pool_private_key = PRIVATE_KEYS[0]

    puzzle_program = make_simple_puzzle_program(PUBLIC_KEYS[1])
    coinbase_coin, coinbase_signature = make_coinbase_coin_and_signature(
        1, puzzle_program, pool_private_key)

    plot_private_key = fake_plot_private_key()
    header_1, header_signature_1 = farm_block(
        mempool, 1, pos_1, coinbase_coin, coinbase_signature, plot_private_key)

    mempool = Mempool(header_1, db)
    mempool.minimum_legal_timestamp = lambda: int(1e10)

    spend_bundle = build_spend_bundle(coinbase_coin, puzzle_program)
    assert spend_bundle.validate_signature()
    mempool.accept_spend_bundle(spend_bundle)

    pool_private_key_2 = PRIVATE_KEYS[1]
    pos_2 = fake_proof_of_space(pool_public_key=PUBLIC_KEYS[1])

    coinbase_coin, coinbase_signature = make_coinbase_coin_and_signature(
        2, puzzle_program, pool_private_key_2)
    header_2, header_signature_2 = farm_block(
        mempool, 2, pos_2, coinbase_coin, coinbase_signature, plot_private_key)
    print(header_2)
    print(header_signature_2)
