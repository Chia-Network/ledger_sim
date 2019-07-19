import asyncio

from chiasim.hack.keys import (
    conditions_for_payment, public_key_bytes_for_index,
    puzzle_hash_for_index, spend_coin
)
from chiasim.hashable import (
    std_hash, EORPrivateKey, HeaderHash, ProgramHash,
    ProofOfSpace, BLSPublicKey, SpendBundle
)
from chiasim.farming import farm_new_block, get_plot_public_key, sign_header
from chiasim.pool import create_coinbase_coin_and_signature, get_pool_public_key
from chiasim.storage import RAM_DB
from chiasim.validation import ChainView, validate_spend_bundle_signature
from chiasim.wallet.deltas import removals_for_body


GENESIS_BLOCK = std_hash(bytes([0]))


def farm_block(
        previous_header, block_number, proof_of_space, spend_bundle, coinbase_puzzle_hash, reward):

    fees_puzzle_hash = puzzle_hash_for_index(3)

    coinbase_coin, coinbase_signature = create_coinbase_coin_and_signature(
        block_number, coinbase_puzzle_hash, reward, proof_of_space.pool_public_key)

    timestamp = int(1e10) + 300 * block_number
    header, body = farm_new_block(
        previous_header, block_number, proof_of_space, spend_bundle,
        coinbase_coin, coinbase_signature, fees_puzzle_hash, timestamp)

    header_signature = sign_header(header, proof_of_space.plot_public_key)

    bad_bls_public_key = BLSPublicKey.from_bin(public_key_bytes_for_index(9))

    bad_eor_public_key = EORPrivateKey(std_hash(bytes([5]))).public_key()

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


def standard_conditions():
    conditions = conditions_for_payment([
        (puzzle_hash_for_index(0), 1000),
        (puzzle_hash_for_index(1), 2000),
    ])
    return conditions


def test_farm_block_empty():
    REWARD = 10000
    unspent_db = RAM_DB()
    chain_view = ChainView.for_genesis_hash(GENESIS_BLOCK, unspent_db)

    pos = ProofOfSpace(get_pool_public_key(), get_plot_public_key())

    puzzle_hash = puzzle_hash_for_index(1)

    spend_bundle = SpendBundle.aggregate([])

    header, header_signature, body = farm_block(
        GENESIS_BLOCK, 1, pos, spend_bundle, puzzle_hash, REWARD)
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

    puzzle_hash = puzzle_hash_for_index(1)

    empty_spend_bundle = SpendBundle.aggregate([])
    header, header_signature, body = farm_block(
        GENESIS_BLOCK, 1, pos, empty_spend_bundle, puzzle_hash, REWARD)
    coinbase_coin = body.coinbase_coin

    conditions = standard_conditions()
    spend_bundle = spend_coin(coin=coinbase_coin, conditions=conditions, index=1)

    header, header_signature, body = farm_block(
        GENESIS_BLOCK, 1, pos, spend_bundle, puzzle_hash, REWARD)
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

    assert chain_view.genesis_hash == GENESIS_BLOCK
    assert chain_view.tip_hash == HeaderHash(GENESIS_BLOCK)
    assert chain_view.tip_index == 0
    assert chain_view.unspent_db == unspent_db

    pos_1 = ProofOfSpace(get_pool_public_key(), get_plot_public_key())

    puzzle_hash = puzzle_hash_for_index(1)

    empty_spend_bundle = SpendBundle.aggregate([])
    header, header_signature, body = farm_block(
        GENESIS_BLOCK, 1, pos_1, empty_spend_bundle, puzzle_hash, REWARD)

    run = asyncio.get_event_loop().run_until_complete
    additions, removals = run(chain_view.accept_new_block(header, header_signature, unspent_db, REWARD))
    assert len(additions) == 2
    assert len(removals) == 0
    # TODO: check additions
    assert additions[1].puzzle_hash == body.fees_coin.puzzle_hash
    assert additions[1].amount == 0

    chain_view = run(chain_view.augment_chain_view(
        header, header_signature, unspent_db, unspent_db, REWARD))

    assert chain_view.genesis_hash == GENESIS_BLOCK
    assert chain_view.tip_hash == HeaderHash(header)
    assert chain_view.tip_index == 1
    assert chain_view.unspent_db == unspent_db

    conditions = standard_conditions()
    spend_bundle_2 = spend_coin(coin=additions[0], conditions=conditions, index=1)

    assert validate_spend_bundle_signature(spend_bundle_2)

    pos_2 = ProofOfSpace(get_pool_public_key(1), get_plot_public_key())

    header_2, header_signature_2, body_2 = farm_block(
        header, 2, pos_2, spend_bundle_2, puzzle_hash, REWARD)
    print(header_2)
    print(header_signature_2)

    removals = removals_for_body(body_2)
    assert len(removals) == 1
    assert removals[0] == list(spend_bundle_2.coin_solutions)[0].coin.coin_name()
