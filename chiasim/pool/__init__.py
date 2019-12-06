from chiasim.atoms import uint64
from chiasim.hashable import BLSPublicKey, BLSSignature, Coin, CoinName, ProgramHash
from chiasim.wallet.BLSHDKey import BLSPrivateHDKey


HIERARCHICAL_PRIVATE_KEY = BLSPrivateHDKey.from_seed(b"foo")
POOL_PRIVATE_KEYS = [HIERARCHICAL_PRIVATE_KEY.private_child(_) for _ in range(100)]
POOL_PUBLIC_KEYS = [_.public_key() for _ in POOL_PRIVATE_KEYS]
POOL_LOOKUP = dict(zip(POOL_PUBLIC_KEYS, POOL_PRIVATE_KEYS))


def get_pool_public_key(index=0) -> BLSPublicKey:
    # TODO: make this configurable
    return POOL_PUBLIC_KEYS[index]


def signature_for_coinbase(coin: Coin, pool_private_key):
    message_hash = coin.name()
    return BLSSignature.create(message_hash, pool_private_key.secret_exponent())


def sign_coinbase_coin(coin: Coin, public_key: BLSPublicKey):
    private_key = POOL_LOOKUP.get(public_key)
    if private_key is None:
        raise ValueError("unknown public key")
    return signature_for_coinbase(coin, private_key)


def create_coinbase_coin(block_index: int, puzzle_hash: ProgramHash, reward: uint64):
    block_index_as_hash = block_index.to_bytes(32, "big")
    return Coin(block_index_as_hash, puzzle_hash, reward)


def create_coinbase_coin_and_signature(
        block_index: int, puzzle_hash: ProgramHash,
        reward: uint64, public_key: BLSPublicKey):
    coin = create_coinbase_coin(block_index, puzzle_hash, reward)
    signature = sign_coinbase_coin(coin, public_key)
    return coin, signature
