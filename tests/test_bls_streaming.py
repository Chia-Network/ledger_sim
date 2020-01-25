# we need to ensure that blspy streams the same way as clvm

import unittest

from clvm.ecdsa.bls12_381 import bls12_381_generator
from clvm.casts import bls12_381_from_bytes, bls12_381_to_bytes

from chiasim.hashable.BLSSignature import BLSPublicKey


class TestBLSStreaming(unittest.TestCase):

    def test_streaming(self):
        for _ in range(1, 128):
            p0 = bls12_381_generator * _
            blob_clvm = bls12_381_to_bytes(p0)
            q0 = BLSPublicKey.from_secret_exponent(_)
            blob_blspy = bytes(q0)
            assert blob_clvm.hex() == blob_blspy.hex()

            p1 = bls12_381_from_bytes(blob_clvm)
            assert p0 == p1

            q1 = BLSPublicKey.from_bytes(blob_blspy)
            assert q0 == q1
