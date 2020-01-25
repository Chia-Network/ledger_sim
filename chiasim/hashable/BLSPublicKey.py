import blspy

from .sized_bytes import bytes48

GROUP_ORDER = (
    52435875175126190479447740508185965837690552500527637822603658699938581184513
)


class BLSPublicKey(bytes48):
    @classmethod
    def from_secret_exponent(cls, secret_exponent):
        secret_exponent %= GROUP_ORDER
        private_key = blspy.PrivateKey.from_bytes(secret_exponent.to_bytes(32, "big"))
        return BLSPublicKey(private_key.get_public_key().serialize())
