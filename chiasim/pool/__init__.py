from chiasim.atoms import uint64
from chiasim.hashable import BLSPublicKey, BLSSignature, Coin, CoinName, ProgramHash
from chiasim.wallet.BLSHDKey import BLSPrivateHDKey


HIERARCHICAL_PRIVATE_KEY = BLSPrivateHDKey.from_seed(b"foo")
POOL_SECRET_EXPONENTS = [
    HIERARCHICAL_PRIVATE_KEY.secret_exponent_for_child(_) for _ in range(100)
]
POOL_PUBLIC_KEYS = [BLSPublicKey.from_secret_exponent(_) for _ in POOL_SECRET_EXPONENTS]
POOL_LOOKUP = dict(zip(POOL_PUBLIC_KEYS, POOL_SECRET_EXPONENTS))


def get_pool_public_key(index=0) -> BLSPublicKey:
    # TODO: make this configurable
    return POOL_PUBLIC_KEYS[index]


def signature_for_coinbase(coin: Coin, secret_exponent):
    message_hash = CoinName(coin)
    return BLSSignature.create(message_hash, secret_exponent)


def sign_coinbase_coin(coin: Coin, public_key: BLSPublicKey):
    secret_exponent = POOL_LOOKUP.get(public_key)
    if secret_exponent is None:
        raise ValueError("unknown public key")
    return signature_for_coinbase(coin, secret_exponent)


def create_coinbase_coin(block_index: int, puzzle_hash: ProgramHash, reward: uint64):
    block_index_as_hash = block_index.to_bytes(32, "big")
    return Coin(block_index_as_hash, puzzle_hash, reward)


def create_coinbase_coin_and_signature(
        block_index: int, puzzle_hash: ProgramHash,
        reward: uint64, public_key: BLSPublicKey):
    coin = create_coinbase_coin(block_index, puzzle_hash, reward)
    signature = sign_coinbase_coin(coin, public_key)
    return coin, signature
