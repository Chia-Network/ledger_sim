import hashlib

from .base import bytes32

Hash = bytes32


def std_hash(b) -> Hash:
    return Hash(hashlib.sha256(b).digest())
