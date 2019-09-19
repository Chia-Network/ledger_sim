from binascii import hexlify
from blspy import PublicKey, Signature
import string
from chiasim.hashable import ProgramHash


def pubkey_format(pubkey):
    if isinstance(pubkey, str):
        if len(pubkey) == 96:
            assert check(pubkey)
            ret = "0x" + pubkey
        elif len(pubkey) == 98:
            assert check(pubkey[2:95])
            assert pubkey[0:1] == "0x"
        else:
            raise ValueError
    elif hasattr(pubkey, 'decode'):  # check if serialized
        ret = serialized_key_to_string(pubkey)
    elif isinstance(pubkey, PublicKey):
        ret = serialized_key_to_string(pubkey.serialize())
    return ret


def serialized_key_to_string(pubkey):
    return "0x%s" % hexlify(pubkey).decode('ascii')


def check(value):
    for letter in value:
        if letter not in string.hexdigits:
            return False
    return True


def puzzlehash_from_string(puzhash):
    return ProgramHash(bytes.fromhex(puzhash))


def pubkey_from_string(pubkey):
    return PublicKey.from_bytes(bytes.fromhex(pubkey))


def signature_from_string(signature):
    breakpoint()
    sig = Signature.from_bytes(bytes.fromhex(signature))
    # sig.sig = bytes(signature)
    return sig
