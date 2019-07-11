import asyncio
import blspy

from chiasim.atoms import uint64
from chiasim.coin.consensus import removals_for_body
from chiasim.hashable import (
    std_hash, Coin, EORPrivateKey,
    ProofOfSpace, BLSSignature, BLSPublicKey, SpendBundle
)
from chiasim.farming import farm_new_block
from chiasim.storage import RAM_DB
from chiasim.validation.chainview import ChainView

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


def farm_block(
        previous_header, block_number, proof_of_space, spend_bundle,
        coinbase_coin, coinbase_signature, plot_private_key):
    # TODO: fix this
    fees_puzzle_hash = fake_hash(100)

    timestamp = int(1e10) + 300 * block_number
    header, body, *rest = farm_new_block(
        previous_header, block_number, proof_of_space, spend_bundle,
        coinbase_coin, coinbase_signature, fees_puzzle_hash, timestamp)

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
    return header, header_signature, body


def test_farm_block_empty():
    # TODO: fix
    FIRST_BLOCK = fake_hash(0)
    unspent_db = RAM_DB()
    chain_view = ChainView.for_genesis_hash(FIRST_BLOCK, unspent_db)

    pos = fake_proof_of_space()

    pool_private_key = PRIVATE_KEYS[0]

    puzzle_program = make_simple_puzzle_program(PUBLIC_KEYS[1])
    coinbase_coin, coinbase_signature = make_coinbase_coin_and_signature(
        1, puzzle_program, pool_private_key)

    spend_bundle = SpendBundle.aggregate([])

    plot_private_key = fake_plot_private_key()
    header, header_signature, body = farm_block(
        FIRST_BLOCK, 1, pos, spend_bundle, coinbase_coin, coinbase_signature, plot_private_key)
    removals = removals_for_body(body)
    assert len(removals) == 0

    run = asyncio.get_event_loop().run_until_complete
    additions, removals = run(chain_view.accept_new_block(header, header_signature, unspent_db))
    assert len(additions) == 2
    assert len(removals) == 0


def test_farm_block_one_spendbundle():
    FIRST_BLOCK = fake_hash(0)
    unspent_db = RAM_DB()
    chain_view = ChainView.for_genesis_hash(FIRST_BLOCK, unspent_db)

    pos = fake_proof_of_space()

    pool_private_key = PRIVATE_KEYS[0]

    puzzle_program = make_simple_puzzle_program(PUBLIC_KEYS[1])
    coinbase_coin, coinbase_signature = make_coinbase_coin_and_signature(
        1, puzzle_program, pool_private_key)

    spend_bundle = build_spend_bundle(coin=coinbase_coin, puzzle_program=puzzle_program)

    plot_private_key = fake_plot_private_key()
    header, header_signature, body = farm_block(
        FIRST_BLOCK, 1, pos, spend_bundle, coinbase_coin, coinbase_signature, plot_private_key)
    removals = removals_for_body(body)
    assert len(removals) == 1
    assert removals[0] == list(spend_bundle.coin_solutions)[0].coin.coin_name()

    run = asyncio.get_event_loop().run_until_complete
    additions, removals = run(chain_view.accept_new_block(header, header_signature, unspent_db))
    assert len(additions) == 4
    assert len(removals) == 1


def test_farm_two_blocks():
    """
    In this test, we farm two blocks: one empty block,
    then one block which spends the coinbase transaction from the empty block.
    """
    FIRST_BLOCK = fake_hash(0)
    unspent_db = RAM_DB()
    chain_view = ChainView.for_genesis_hash(FIRST_BLOCK, unspent_db)

    pos_1 = fake_proof_of_space()

    pool_private_key = PRIVATE_KEYS[0]

    puzzle_program = make_simple_puzzle_program(PUBLIC_KEYS[1])
    coinbase_coin, coinbase_signature = make_coinbase_coin_and_signature(
        1, puzzle_program, pool_private_key)

    empty_spend_bundle = SpendBundle.aggregate([])
    plot_private_key = fake_plot_private_key()
    header, header_signature, body = farm_block(
        FIRST_BLOCK, 1, pos_1, empty_spend_bundle, coinbase_coin, coinbase_signature, plot_private_key)

    run = asyncio.get_event_loop().run_until_complete
    additions, removals = run(chain_view.accept_new_block(header, header_signature, unspent_db))
    assert len(additions) == 2
    assert len(removals) == 0
    # TODO: check additions
    assert additions[1].puzzle_hash == fake_hash(100)
    assert additions[1].amount == 0

    # TODO: create another chain view
    spend_bundle_2 = build_spend_bundle(coinbase_coin, puzzle_program)
    assert spend_bundle_2.validate_signature()

    pool_private_key_2 = PRIVATE_KEYS[1]
    pos_2 = fake_proof_of_space(pool_public_key=PUBLIC_KEYS[1])

    coinbase_coin, coinbase_signature = make_coinbase_coin_and_signature(
        2, puzzle_program, pool_private_key_2)
    header_2, header_signature_2, body_2 = farm_block(
        header, 2, pos_2, spend_bundle_2, coinbase_coin, coinbase_signature, plot_private_key)
    print(header_2)
    print(header_signature_2)

    removals = removals_for_body(body_2)
    assert len(removals) == 1
    assert removals[0] == list(spend_bundle_2.coin_solutions)[0].coin.coin_name()
