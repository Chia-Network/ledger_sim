import blspy

from chiasim.atoms import uint64
from chiasim.hashable import (
    std_hash, Coin, EORPrivateKey,
    ProofOfSpace, BLSSignature, BLSPublicKey
)
from chiasim.farming import Mempool

from .helpers import build_spend_bundle, make_simple_puzzle_program, PRIVATE_KEYS, PUBLIC_KEYS


# pool manager function
def make_coinbase_coin_and_signature(block_index, puzzle_hash, pool_private_key):
    block_index_as_hash = block_index.to_bytes(32, "big")
    coin = Coin(block_index_as_hash, puzzle_hash, uint64(10000))
    message_hash = blspy.Util.hash256(coin.as_bin())
    sig = pool_private_key.sign_prepend_prehashed(message_hash)
    signature = BLSSignature(sig.serialize())
    return coin, signature


def fake_hash(v):
    return std_hash(bytes([v]))


def farm_block(mempool, block_number):
    eprv_k = blspy.ExtendedPrivateKey.from_seed(b"foo")
    pool_private_key = eprv_k.private_child(0).get_private_key()

    # TODO: fix this
    puzzle_hash = fake_hash(3)

    coinbase_coin, coinbase_signature = make_coinbase_coin_and_signature(1, puzzle_hash, pool_private_key)

    # TODO: fix this
    plot_private_key = EORPrivateKey(fake_hash(4))
    plot_public_key = plot_private_key.public_key()

    # TODO: fix this
    fees_puzzle_hash = fake_hash(100)

    pool_public_key = BLSPublicKey.from_bin(pool_private_key.get_public_key().serialize())
    proof_of_space = ProofOfSpace(pool_public_key, plot_public_key)
    header, body, additions, removals = mempool.farm_new_block(
        block_number, proof_of_space, coinbase_coin, coinbase_signature, fees_puzzle_hash)

    header_signature = plot_private_key.sign(header.hash())

    bad_bls_public_key = BLSPublicKey.from_bin(PRIVATE_KEYS[1].get_public_key().serialize())

    bad_eor_public_key = EORPrivateKey(fake_hash(5)).public_key()

    hkp = header_signature.pair(header.hash(), proof_of_space.plot_public_key)
    _ = header_signature.validate([hkp])
    assert _

    hkp = header_signature.pair(header.hash(), bad_eor_public_key)
    assert not header_signature.validate([hkp])

    hkp = body.coinbase_signature.pair(body.coinbase_coin.hash(), proof_of_space.pool_public_key)
    assert body.coinbase_signature.validate([hkp])

    hkp = body.coinbase_signature.pair(body.coinbase_coin.hash(), bad_bls_public_key)
    assert not body.coinbase_signature.validate([hkp])
    return header, header_signature


def test_farm_block_empty():
    # TODO: fix
    FIRST_BLOCK = fake_hash(0)

    mempool = Mempool(FIRST_BLOCK)
    mempool.minimum_legal_timestamp = lambda: int(1e10)
    farm_block(mempool, 1)


def test_farm_block_one_spendbundle():
    FIRST_BLOCK = fake_hash(0)

    mempool = Mempool(FIRST_BLOCK)
    mempool.minimum_legal_timestamp = lambda: int(1e10)

    spend_bundle = build_spend_bundle()
    mempool.accept_spend_bundle(spend_bundle)
    farm_block(mempool, 2)
