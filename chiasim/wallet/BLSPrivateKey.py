import dataclasses

import blspy

from chiasim.hashable import bytes32, BLSSignature, BLSPublicKey


@dataclasses.dataclass
class BLSPrivateKey:

    pk: blspy.PrivateKey

    def sign(self, message_hash: bytes32) -> BLSSignature:
        return BLSSignature(self.pk.sign_prepend_prehashed(message_hash).serialize())

    def public_key(self) -> BLSPublicKey:
        return BLSPublicKey(self.pk.get_public_key().serialize())
