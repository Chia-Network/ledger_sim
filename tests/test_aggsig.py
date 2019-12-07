from chiasim.hashable import BLSPublicKey, BLSSignature
from chiasim.hashable.Message import bls_hash
from chiasim.wallet.BLSHDKey import BLSPrivateHDKey


def test_BLSSignature():
    eprv_k = BLSPrivateHDKey.from_seed(b"foo")
    sec_k = eprv_k.secret_exponent()
    pub_k = BLSPublicKey.from_secret_exponent(sec_k)
    msg = b"bar"
    msg_hash = bls_hash(msg)
    sig = BLSSignature.create(msg_hash, sec_k)
    print(sig)
    pair = sig.aggsig_pair(pub_k, msg_hash)
    ok = sig.validate([pair])
    assert ok

    eprv_k2 = BLSPrivateHDKey.from_seed(b"foobar")
    sec_k2 = eprv_k2.secret_exponent()
    pub_k2 = BLSPublicKey.from_secret_exponent(sec_k2)
    pair = sig.aggsig_pair(pub_k2, msg_hash)
    ok = sig.validate([pair])
    assert not ok


def test_BLSSignature_aggregate():
    eprv_k = BLSPrivateHDKey.from_seed(b"foo")

    sec_0 = eprv_k.private_hd_child(0).secret_exponent()
    pub_0 = BLSPublicKey.from_secret_exponent(sec_0)
    sec_1 = eprv_k.private_hd_child(1).secret_exponent()
    pub_1 = BLSPublicKey.from_secret_exponent(sec_1)

    msg_0 = b"bar"
    msg_0_hash = bls_hash(msg_0)

    sig_0 = BLSSignature.create(msg_0_hash, sec_0)
    print(sig_0)
    pair_0 = sig_0.aggsig_pair(pub_0, msg_0_hash)
    ok = sig_0.validate([pair_0])
    assert ok

    pair_0_bad = sig_0.aggsig_pair(pub_1, msg_0_hash)
    ok = sig_0.validate([pair_0_bad])
    assert not ok

    msg_1 = b"baz"
    msg_1_hash = bls_hash(msg_1)

    sig_1 = BLSSignature.create(msg_1_hash, sec_1)
    print(sig_1)
    pair_1 = sig_1.aggsig_pair(pub_1, msg_1_hash)
    ok = sig_1.validate([pair_1])
    assert ok

    total_sig = sig_0.aggregate([sig_0, sig_1])
    ok = total_sig.validate([pair_0, pair_1])
    assert ok
