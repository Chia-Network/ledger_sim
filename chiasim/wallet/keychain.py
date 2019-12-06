from chiasim.hashable import BLSPublicKey, BLSSignature
from chiasim.validation.Conditions import conditions_by_opcode
from chiasim.validation.consensus import (
    conditions_for_solution,
    hash_key_pairs_for_conditions_dict,
)


class Keychain(dict):
    @classmethod
    def __new__(cls, *args):
        return dict.__new__(*args)

    def add_secret_exponents(self, secret_exponents):
        for _ in secret_exponents:
            public_key = BLSPublicKey.from_secret_exponent(_)
            self[public_key] = _

    def sign(self, aggsig_pair):
        secret_exponent = self.get(aggsig_pair.public_key)
        if not secret_exponent:
            raise ValueError("unknown pubkey %s" % aggsig_pair.public_key)
        return BLSSignature.create(aggsig_pair.message_hash, secret_exponent)

    def signature_for_solution(self, solution):
        signatures = []
        conditions_dict = conditions_by_opcode(conditions_for_solution(solution))
        for _ in hash_key_pairs_for_conditions_dict(conditions_dict):
            signature = self.sign(_)
            signatures.append(signature)
        return BLSSignature.aggregate(signatures)
