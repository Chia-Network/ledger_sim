import blspy

from .sized_bytes import bytes48


class BLSPublicKey(bytes48):
    @classmethod
    def from_secret_exponent(cls, secret_exponent):
        private_key = blspy.PrivateKey.from_bytes(secret_exponent.to_bytes(32, "big"))
        return BLSPublicKey(private_key.get_public_key().serialize())
