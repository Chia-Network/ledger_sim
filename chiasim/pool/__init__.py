import blspy

from chiasim.atoms import uint64
from chiasim.hashable import BLSPublicKey, BLSSignature, Coin, ProgramHash


HIERARCHICAL_PRIVATE_KEY = blspy.ExtendedPrivateKey.from_seed(b"foo")
POOL_PRIVATE_KEY = HIERARCHICAL_PRIVATE_KEY.private_child(0).get_private_key()
POOL_PUBLIC_KEY = BLSPublicKey.from_bin(POOL_PRIVATE_KEY.get_public_key().serialize())


def get_pool_public_key() -> BLSPublicKey:
    # TODO: make this configurable
    return POOL_PUBLIC_KEY


def signature_for_coinbase(coin: Coin, pool_private_key: blspy.PrivateKey):
    message_hash = blspy.Util.hash256(coin.as_bin())
    return BLSSignature(pool_private_key.sign_prepend_prehashed(message_hash).serialize())


def sign_coinbase_coin(coin: Coin, public_key: BLSPublicKey):
    if public_key != public_key:
        raise ValueError("unknown public key")
    return signature_for_coinbase(coin, POOL_PRIVATE_KEY)


def create_coinbase_coin(block_index: int, puzzle_hash: ProgramHash, reward: uint64):
    block_index_as_hash = block_index.to_bytes(32, "big")
    return Coin(block_index_as_hash, puzzle_hash, reward)


def create_coinbase_coin_and_signature(
        block_index: int, puzzle_hash: ProgramHash,
        reward: uint64, public_key: BLSPublicKey):
    coin = create_coinbase_coin(block_index, puzzle_hash, reward)
    signature = sign_coinbase_coin(coin, public_key)
    return coin, signature
