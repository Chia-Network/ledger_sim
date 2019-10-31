import hashlib

from .sized_bytes import bytes32


Hash = bytes32


def std_hash(b) -> Hash:
    """
    The standard hash used in many places.
    """
    return Hash(hashlib.sha256(b).digest())


class Hashable:
    """
    A mix-in class that allows an object to take a hash of itself.
    """
    def hash(self):
        return std_hash(bytes(self))
