import hashlib

from ..atoms import bytes32

Hash = bytes32


def std_hash(b) -> Hash:
    return Hash(hashlib.sha256(b).digest())


class Hashable:
    def hash(self):
        return std_hash(self.as_bin())
