import collections
import time

from clvm import to_sexp_f

from opacity import binutils

from chiasim.atoms import hexbytes
from chiasim.coin.consensus import additions_for_body, removals_for_body
from chiasim.hashable import (
    BLSSignature, Body, Coin, Header, HeaderHash,
    Program, ProgramHash, ProofOfSpace, SpendBundle, Unspent
)
from chiasim.storage.Storage import Storage


def best_solution_program(bundle: SpendBundle):
    """
    This could potentially do a lot of clever and complicated compression
    optimizations in conjunction with choosing the set of SpendBundles to include.

    For now, we just quote the solutions we know.
    """
    r = []
    for coin_solution in bundle.coin_solutions:
        entry = [coin_solution.coin.coin_name(), coin_solution.solution.code]
        r.append(entry)
    return Program(to_sexp_f([binutils.assemble("#q"), r]))


class Mempool:
    """
    A mempool contains a list of consistent removals and solutions.
    """
    def __init__(self, tip: HeaderHash, storage: Storage):
        self.reset_tip(tip)
        self._storage = storage
        self._next_block_index = 1

    def reset_tip(self, tip: HeaderHash):
        self._bundles = set()
        self._tip = tip

    def collect_best_bundle(self) -> SpendBundle:
        # this is way too simple
        spend_bundle = SpendBundle.aggregate(self._bundles)
        assert spend_bundle.fees() >= 0
        return spend_bundle

    def minimum_legal_timestamp(self):
        return 0

    def generate_timestamp(self):
        return max(self.minimum_legal_timestamp(), int(time.time()))

    async def farm_new_block(
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

        for coin in best_bundle.additions():
            await self._storage.add_preimage(coin.as_bin())

        assert best_bundle.validate_signature()
        solution_program = best_solution_program(best_bundle)
        extension_data = hexbytes(b'')

        block_index_hash = block_index.to_bytes(32, "big")
        fees_coin = Coin(block_index_hash, fees_puzzle_hash, best_bundle.fees())
        body = Body(
            coinbase_signature, coinbase_coin, fees_coin,
            solution_program, program_cost, best_bundle.aggregated_signature)
        timestamp = self.generate_timestamp()

        header = Header(self._tip, timestamp, proof_of_space, body, extension_data)

        self.reset_tip(header)

        return header, body

        # still need to do the following:
        # private_key = private_for_public(proof_of_space.plot_pubkey)
        # header_signature = private_key.sign(std_hash(header.as_bin()))

    def accept_spend_bundle(self, spend_bundle):
        self._bundles.add(spend_bundle)

    async def validate_spend_bundle(self, spend_bundle):
        # validate that this bundle is correct and consistent
        # with the current mempool state
        if not spend_bundle.validate_signature():
            raise ValueError("bad signature")
        for coin_solution in spend_bundle.coin_solutions:
            coin = coin_solution.coin
            coin_name = coin.coin_name()
            unspent = await self._storage.unspent_for_coin_name(coin_name)
            if unspent is None:
                raise ValueError("unknown spendable %s" % coin_name)
            if unspent.confirmed_block_index >= self._next_block_index:
                raise ValueError("spendable %s not confirmed at index %d" % (
                    coin_name, self._next_block_index - 1))
            if unspent.spent_block_index != 0:
                raise ValueError("spendable %s already spent" % coin_name)

    def next_block_index(self):
        return self._next_block_index

    async def accept_new_block(self, block_index, body):
        additions = additions_for_body(body, self._storage)
        removals = removals_for_body(body)

        if removals and max(collections.Counter(removals).values()) > 1:
            raise ValueError("double spend")

        await self._storage.add_preimage(body.coinbase_coin.coin_name_data().as_bin())
        await self._storage.add_preimage(body.fees_coin.coin_name_data().as_bin())

        async for coin in additions:
            coin_name = coin.coin_name()
            unspent = Unspent(coin.amount, block_index, 0)
            await self._storage.set_unspent_for_coin_name(coin_name, unspent)
            await self._storage.add_preimage(coin.coin_name_data().as_bin())

        for coin_name in removals:
            unspent = await self._storage.unspent_for_coin_name(coin_name)
            unspent = Unspent(unspent.amount, unspent.confirmed_block_index, block_index)
            await self._storage.set_unspent_for_coin_name(coin_name, unspent)

        self._next_block_index = block_index + 1