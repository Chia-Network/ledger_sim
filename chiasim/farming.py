import time

from clvm import to_sexp_f

from .atoms import hexbytes


from .hashable import (
    BLSSignature, Body, Coin, Header,
    HeaderHash, Program, ProgramHash, ProofOfSpace, SpendBundle
)


def best_solution_program(bundle: SpendBundle):
    # this could potentially get very complicated and clever
    # the first attempt should just return a quoted version of all the solutions
    # for now, return a (bad) blank solution
    return Program(to_sexp_f([]))


class Mempool:
    """
    A mempool contains a list of consistent removals and solutions
    """
    def __init__(self, tip: HeaderHash):
        self.reset_tip(tip)

    def reset_tip(self, tip: HeaderHash):
        self._bundles = set()
        self._tip = tip

    def collect_best_bundle(self) -> SpendBundle:
        # this is way too simple
        total = SpendBundle.aggregate(self._bundles)
        return total

    def minimum_legal_timestamp(self):
        return 0

    def generate_timestamp(self):
        return max(self.minimum_legal_timestamp(), int(time.time()))

    def farm_new_block(
            self, block_index: int, proof_of_space: ProofOfSpace,
            coinbase_coin: Coin, coinbase_signature: BLSSignature,
            fees_puzzle_hash: ProgramHash):
        """
        Steps:
            - collect up a consistent set of removals and solutions
            - run solutions to get the additions
            - select a timestamp = max(now, minimum_legal_timestamp)
            - create blank extension data
            - collect up coinbase coin with coinbase signature (if solo mining, we get these locally)
            - return Header, HeaderSignature, Body, Additions and Removals
        """

        program_cost = 0
        best_bundle = self.collect_best_bundle()
        additions = best_bundle.additions()
        removals = best_bundle.removals()
        solution_program = best_solution_program(best_bundle)
        extension_data = hexbytes(b'')

        block_index_hash = block_index.to_bytes(32, "big")
        fees_coin = Coin(block_index_hash, fees_puzzle_hash, best_bundle.fees())
        body = Body(
            coinbase_signature, coinbase_coin, fees_coin,
            solution_program, program_cost, best_bundle.aggregated_signature)
        timestamp = self.generate_timestamp()

        removal_names = tuple(_.coin_name() for _ in removals)
        header = Header(
            self._tip, timestamp, additions, removal_names,
            proof_of_space, body, extension_data)

        self.reset_tip(header)

        return header, body, additions, removals

        # still need to do the following:
        # private_key = private_for_public(proof_of_space.plot_pubkey)
        # header_signature = private_key.sign(std_hash(header.as_bin()))

    def accept_spend_bundle(self, spend_bundle):
        # TODO: validate that this bundle is correct and consistent
        # with the current mempool state
        self._bundles.add(spend_bundle)

    def next_block_number(self):
        # TODO: fix this
        return 1
