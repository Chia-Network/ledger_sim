from chiasim.hashable.BLSSignature import BLSPublicKey
from chiasim.hashable.Message import bls_hash
from chiasim.wallet.BLSHDKey import BLSPrivateHDKey


def test_BLSSignature():
    eprv_k = BLSPrivateHDKey.from_seed(b"foo")
    prv_k = eprv_k.private_key()
    pub_k = prv_k.public_key()
    msg = b"bar"
    msg_hash = bls_hash(msg)
    sig = prv_k.sign(msg_hash)
    print(sig)
    pair = sig.aggsig_pair(pub_k, msg_hash)
    ok = sig.validate([pair])
    assert ok

    eprv_k2 = BLSPrivateHDKey.from_seed(b"foobar")
    prv_k2 = eprv_k2.private_key()
    pub_k2 = prv_k2.public_key()
    pair = sig.aggsig_pair(pub_k2, msg_hash)
    ok = sig.validate([pair])
    assert not ok


def test_BLSSignature_aggregate():
    eprv_k = BLSPrivateHDKey.from_seed(b"foo")

    prv_0 = eprv_k.private_hd_child(0).private_key()
    pub_0 = prv_0.public_key()
    prv_1 = eprv_k.private_hd_child(1).private_key()
    pub_1 = prv_1.public_key()

    msg_0 = b"bar"
    msg_0_hash = bls_hash(msg_0)

    sig_0 = prv_0.sign(msg_0_hash)
    print(sig_0)
    pair_0 = sig_0.aggsig_pair(pub_0, msg_0_hash)
    ok = sig_0.validate([pair_0])
    assert ok

    pair_0_bad = sig_0.aggsig_pair(pub_1, msg_0_hash)
    ok = sig_0.validate([pair_0_bad])
    assert not ok

    msg_1 = b"baz"
    msg_1_hash = bls_hash(msg_1)

    sig_1 = prv_1.sign(msg_1_hash)
    print(sig_1)
    pair_1 = sig_1.aggsig_pair(pub_1, msg_1_hash)
    ok = sig_1.validate([pair_1])
    assert ok

    total_sig = sig_0.aggregate([sig_0, sig_1])
    ok = total_sig.validate([pair_0, pair_1])
    assert ok
