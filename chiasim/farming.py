import time

from .hashable.Body import Solution
from .hashable.Header import Extension


from .hashable import (
    Body, Hash, SpendBundle, uint64, Header,
    Coin, ProofOfSpace, EORPrivateKey, Signature
)


def best_solution_program(bundle: SpendBundle):
    # this could potentially get very complicated and clever
    # for now, just return a quoted version of all the solutions
    return Solution(b'')


def private_for_public(pk):
    # this works for EOR private keys only
    return EORPrivateKey(pk)


class Mempool:
    """
    A mempool contains a list of consisten removals and solutions
    """
    def __init__(self, tip: Hash):
        self._bundles = set()
        self._tip = tip

    def collect_best_bundle(self) -> SpendBundle:
        # this is way too simple
        total = SpendBundle([], Signature.zero())
        for _ in self._bundles:
            total += _
        return total

    def minimum_legal_timestamp(self):
        return 0

    def generate_timestamp(self):
        return uint64(max(self.minimum_legal_timestamp(), int(time.time())))

    def farm_new_block(
            self, proof_of_space: ProofOfSpace,
            coinbase_coin: Coin, coinbase_signature: Signature,
            fees_puzzle_hash: Hash):
        """
        Steps:
            - collect up a consistent set of removals and solutions
            - run solutions to get the additions
            - select a timestamp = max(now, minimum_legal_timestamp)
            - create blank extension data
            - collect up coinbase coin with coinbase signature (if solo mining, we get these locally)
            - return Header, HeaderSignature, Body, Additions and Removals
        """

        program_cost = uint64(0)
        best_bundle = self.collect_best_bundle()
        additions = best_bundle.additions()
        removals = best_bundle.removals()
        solution_program = best_solution_program(best_bundle)
        extension_data = Extension(b'')

        fees_coin = Coin(fees_puzzle_hash, best_bundle.fees())
        body = Body(
            coinbase_signature, coinbase_coin, fees_coin,
            solution_program, program_cost, best_bundle.aggregated_solution_signature)
        timestamp = self.generate_timestamp()

        header = Header(
            self._tip, timestamp, additions, removals,
            proof_of_space, body, extension_data)

        private_key = private_for_public(proof_of_space.plot_pubkey)
        header_signature = private_key.sign(header.hash())

        return header, header_signature, body, additions, removals

    def accept_spend_bundle(self, spend_bundle):
        # TODO: validate that this bundle is correct and consistent
        # with the current mempool state
        self._bundles.add(spend_bundle)
