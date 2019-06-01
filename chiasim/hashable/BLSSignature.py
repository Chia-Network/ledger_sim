from typing import List

import blspy

from ..atoms import bytes48, bytes96, streamable
from ..atoms.bin_methods import bin_methods

from .Message import MessageHash


ZERO96 = bytes96([0] * 96)


class BLSPublicKey(bytes48):
    pass


@streamable
class BLSSignature(bin_methods):
    sig: bytes96

    @classmethod
    def aggregate(cls, sigs):
        if len(sigs) == 0:
            sig = ZERO96
        else:
            sig = blspy.PrependSignature.aggregate(_.sig for _ in sigs if _.sig != ZERO96)
        return cls(sig)

    def validate(self, message_hashes: List[MessageHash], pubkeys: List[BLSPublicKey]) -> bool:
        # check for special case of 0
        if self.sig == ZERO96:
            if len(message_hashes) == 0 or len(pubkeys) == 0:
                return True
        return blspy.PrependSignature.from_bytes(self.sig).verify(
            message_hashes, [blspy.PublicKey.from_bytes(_) for _ in pubkeys])
