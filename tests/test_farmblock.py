import asyncio

from chiasim.hashable import (
    std_hash, EORPrivateKey, Program, ProgramHash,
    ProofOfSpace, BLSPublicKey, SpendBundle
)
from chiasim.farming import farm_new_block, get_plot_public_key, sign_header
from chiasim.pool import create_coinbase_coin_and_signature, get_pool_public_key
from chiasim.storage import RAM_DB
from chiasim.validation import ChainView, validate_spend_bundle_signature
from chiasim.validation.consensus import removals_for_body

from .helpers import build_spend_bundle, make_simple_puzzle_program, PRIVATE_KEYS, PUBLIC_KEYS


def fake_hash(v):
    return std_hash(bytes([v]))


GENESIS_BLOCK = std_hash(bytes([0]))


def farm_block(
        previous_header, block_number, proof_of_space, spend_bundle, coinbase_puzzle_program, reward):

    # TODO: fix this
    fees_puzzle_hash = fake_hash(100)

    coinbase_coin, coinbase_signature = create_coinbase_coin_and_signature(
        block_number, ProgramHash(Program(coinbase_puzzle_program)), reward, proof_of_space.pool_public_key)

    timestamp = int(1e10) + 300 * block_number
    header, body, *rest = farm_new_block(
        previous_header, block_number, proof_of_space, spend_bundle,
        coinbase_coin, coinbase_signature, fees_puzzle_hash, timestamp)

    header_signature = sign_header(header, proof_of_space.plot_public_key)

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
    REWARD = 10000
    unspent_db = RAM_DB()
    chain_view = ChainView.for_genesis_hash(GENESIS_BLOCK, unspent_db)

    pos = ProofOfSpace(get_pool_public_key(), get_plot_public_key())

    puzzle_program = make_simple_puzzle_program(PUBLIC_KEYS[1])

    spend_bundle = SpendBundle.aggregate([])

    header, header_signature, body = farm_block(
        GENESIS_BLOCK, 1, pos, spend_bundle, puzzle_program, REWARD)
    removals = removals_for_body(body)
    assert len(removals) == 0

    run = asyncio.get_event_loop().run_until_complete
    additions, removals = run(chain_view.accept_new_block(header, header_signature, unspent_db, REWARD))
    assert len(additions) == 2
    assert len(removals) == 0


def test_farm_block_one_spendbundle():
    REWARD = 10000
    unspent_db = RAM_DB()
    chain_view = ChainView.for_genesis_hash(GENESIS_BLOCK, unspent_db)

    pos = ProofOfSpace(get_pool_public_key(), get_plot_public_key())

    puzzle_program = make_simple_puzzle_program(PUBLIC_KEYS[1])

    empty_spend_bundle = SpendBundle.aggregate([])
    header, header_signature, body = farm_block(
        GENESIS_BLOCK, 1, pos, empty_spend_bundle, puzzle_program, REWARD)
    coinbase_coin = body.coinbase_coin

    spend_bundle = build_spend_bundle(coin=coinbase_coin, puzzle_program=puzzle_program)

    header, header_signature, body = farm_block(
        GENESIS_BLOCK, 1, pos, spend_bundle, puzzle_program, REWARD)
    removals = removals_for_body(body)
    assert len(removals) == 1
    assert removals[0] == list(spend_bundle.coin_solutions)[0].coin.coin_name()

    run = asyncio.get_event_loop().run_until_complete
    additions, removals = run(chain_view.accept_new_block(header, header_signature, unspent_db, REWARD))
    assert len(additions) == 4
    assert len(removals) == 1


def test_farm_two_blocks():
    """
    In this test, we farm two blocks: one empty block,
    then one block which spends the coinbase transaction from the empty block.
    """
    REWARD = 10000
    unspent_db = RAM_DB()
    chain_view = ChainView.for_genesis_hash(GENESIS_BLOCK, unspent_db)

    pos_1 = ProofOfSpace(get_pool_public_key(), get_plot_public_key())

    puzzle_program = make_simple_puzzle_program(PUBLIC_KEYS[1])

    empty_spend_bundle = SpendBundle.aggregate([])
    header, header_signature, body = farm_block(
        GENESIS_BLOCK, 1, pos_1, empty_spend_bundle, puzzle_program, REWARD)

    run = asyncio.get_event_loop().run_until_complete
    additions, removals = run(chain_view.accept_new_block(header, header_signature, unspent_db, REWARD))
    assert len(additions) == 2
    assert len(removals) == 0
    # TODO: check additions
    assert additions[1].puzzle_hash == fake_hash(100)
    assert additions[1].amount == 0

    # TODO: create another chain view
    spend_bundle_2 = build_spend_bundle(additions[0], puzzle_program)
    assert validate_spend_bundle_signature(spend_bundle_2)

    pos_2 = ProofOfSpace(get_pool_public_key(1), get_plot_public_key())

    header_2, header_signature_2, body_2 = farm_block(
        header, 2, pos_2, spend_bundle_2, puzzle_program, REWARD)
    print(header_2)
    print(header_signature_2)

    removals = removals_for_body(body_2)
    assert len(removals) == 1
    assert removals[0] == list(spend_bundle_2.coin_solutions)[0].coin.coin_name()
