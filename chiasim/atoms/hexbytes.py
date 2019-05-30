import binascii


class hexbytes(bytes):
    def as_bin(self) -> "hexbytes":
        return self

    def __str__(self):
        return binascii.hexlify(self).decode("utf8")

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, str(self))
