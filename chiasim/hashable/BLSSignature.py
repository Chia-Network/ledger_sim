from typing import List

import blspy

from ..atoms import streamable

from .sized_bytes import bytes96

from .BLSPublicKey import BLSPublicKey
from .Message import MessageHash


GROUP_ORDER = (
    52435875175126190479447740508185965837690552500527637822603658699938581184513
)

ZERO96 = bytes96([0] * 96)


@streamable
class BLSSignature:
    """
    This wraps the blspy.BLSPublicKey and resolves a couple edge cases around aggregation and validation.
    """

    @streamable
    class aggsig_pair:
        public_key: BLSPublicKey
        message_hash: MessageHash

    sig: bytes96

    @classmethod
    def create(cls, message_hash, secret_exponent):
        secret_exponent %= GROUP_ORDER
        private_key = blspy.PrivateKey.from_bytes(secret_exponent.to_bytes(32, "big"))
        return BLSSignature(
            private_key.sign_prepend_prehashed(message_hash).serialize()
        )

    @classmethod
    def aggregate(cls, sigs):
        sigs = [_ for _ in sigs if _.sig != ZERO96]
        if len(sigs) == 0:
            sig = ZERO96
        else:
            wrapped_sigs = [blspy.PrependSignature.from_bytes(_.sig) for _ in sigs]
            sig = blspy.PrependSignature.aggregate(wrapped_sigs).serialize()
        return cls(sig)

    def validate(self, hash_key_pairs: List[aggsig_pair]) -> bool:
        # check for special case of 0
        if len(hash_key_pairs) == 0:
            return True
        message_hashes = [_.message_hash for _ in hash_key_pairs]
        public_keys = [blspy.PublicKey.from_bytes(_.public_key) for _ in hash_key_pairs]
        try:
            # when the signature is invalid, this method chokes
            signature = blspy.PrependSignature.from_bytes(self.sig)
            return signature.verify(message_hashes, public_keys)
        except Exception as ex:
            return False
