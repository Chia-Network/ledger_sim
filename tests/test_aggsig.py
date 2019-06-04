import dataclasses

import blspy

from chiasim.atoms import bytes32
from chiasim.hashable.BLSSignature import BLSSignature, BLSPublicKey
from chiasim.hashable.Message import bls_hash


@dataclasses.dataclass
class BLSPrivateKey:

    pk: blspy.PrivateKey

    def sign(self, message_hash: bytes32) -> BLSSignature:
        return BLSSignature(self.pk.sign_prepend_prehashed(message_hash).serialize())

    def public_key(self) -> BLSPublicKey:
        return BLSPublicKey(self.pk.get_public_key())


def test_BLSSignature():
    eprv_k = blspy.ExtendedPrivateKey.from_seed(b"foo")
    prv_k = eprv_k.get_private_key()
    pub_k = prv_k.get_public_key()
    bls_prv_k = BLSPrivateKey(prv_k)
    msg = b"bar"
    msg_hash = bls_hash(msg)
    sig = bls_prv_k.sign(msg_hash)
    print(sig)
    pair = sig.pair(msg_hash, BLSPublicKey(pub_k.serialize()))
    ok = sig.validate([pair])
    assert ok

    eprv_k2 = blspy.ExtendedPrivateKey.from_seed(b"foobar")
    prv_k2 = eprv_k2.get_private_key()
    pub_k2 = prv_k2.get_public_key()
    pair = sig.pair(msg_hash, BLSPublicKey(pub_k2.serialize()))
    ok = sig.validate([pair])
    assert not ok


def test_BLSSignature_aggregate():
    eprv_k = blspy.ExtendedPrivateKey.from_seed(b"foo")

    prv_0 = eprv_k.private_child(0).get_private_key()
    pub_0 = prv_0.get_public_key()
    prv_1 = eprv_k.private_child(1).get_private_key()
    pub_1 = prv_1.get_public_key()

    bls_prv_0 = BLSPrivateKey(prv_0)
    msg_0 = b"bar"
    msg_0_hash = bls_hash(msg_0)

    sig_0 = bls_prv_0.sign(msg_0_hash)
    print(sig_0)
    pair_0 = sig_0.pair(msg_0_hash, BLSPublicKey(pub_0.serialize()))
    ok = sig_0.validate([pair_0])
    assert ok

    pair_0_bad = sig_0.pair(msg_0_hash, BLSPublicKey(pub_1.serialize()))
    ok = sig_0.validate([pair_0_bad])
    assert not ok

    bls_prv_1 = BLSPrivateKey(prv_1)
    msg_1 = b"baz"
    msg_1_hash = bls_hash(msg_1)

    sig_1 = bls_prv_1.sign(msg_1_hash)
    print(sig_1)
    pair_1 = sig_1.pair(msg_1_hash, BLSPublicKey(pub_1.serialize()))
    ok = sig_1.validate([pair_1])
    assert ok

    total_sig = sig_0.aggregate([sig_0, sig_1])
    ok = total_sig.validate([pair_0, pair_1])
    assert ok
