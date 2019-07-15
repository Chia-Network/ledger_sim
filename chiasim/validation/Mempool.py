import collections
import time

from .consensus import additions_for_body, removals_for_body
from chiasim.hashable import (
    HeaderHash, SpendBundle, Unspent
)
from chiasim.storage import Storage


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
