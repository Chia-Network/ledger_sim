import asyncio
import datetime
import logging
import time

from chiasim.atoms import uint64
from chiasim.farming import farm_new_block, get_plot_public_key, sign_header
from chiasim.hashable import (
    HeaderHash, ProgramHash, ProofOfSpace, SpendBundle
)
from chiasim.pool import create_coinbase_coin_and_signature, get_pool_public_key
from chiasim.remote.api_decorators import api_request
from chiasim.validation import ChainView, validate_spend_bundle_signature

log = logging.getLogger(__name__)


GENESIS_HASH = bytes([0] * 32)


class LedgerAPI:
    def __init__(self, block_tip: HeaderHash, block_index: uint64, storage):
        self._tip = block_tip
        self._block_index = block_index

        self._chain_view = ChainView.for_genesis_hash(GENESIS_HASH, storage)
        self._storage = storage
        self._spend_bundles = []
        self._next_block_lock = asyncio.Lock()

    async def do_ping(self, m=None):
        log.info("ping")
        return dict(response="got ping message %r at time %s" % (
            m, datetime.datetime.utcnow()))

    @api_request(tx=SpendBundle.from_bin)
    async def do_push_tx(self, tx):
        log.info("push_tx %s", tx)
        if not validate_spend_bundle_signature(tx):
            raise ValueError("bad signature on %s" % tx)

        self._spend_bundles.append(tx)
        # TODO: ensure that we can farm a block even after adding this spend_bundle
        # Otherwise, it's inconsistent with the mempool
        return dict(response="accepted %s" % tx)

    async def do_get_tip(self):
        log.info("get_tip")
        chain_view = self._chain_view
        return dict(
            tip_hash=chain_view.tip_hash, tip_index=chain_view.tip_index,
            genesis_hash=chain_view.genesis_hash)

    @api_request(
        coinbase_puzzle_hash=ProgramHash.from_bin,
        fees_puzzle_hash=ProgramHash.from_bin,
    )
    async def do_next_block(self, coinbase_puzzle_hash, fees_puzzle_hash):
        async with self._next_block_lock:
            block_number = self._chain_view.tip_index + 1

            REWARD = int(1e9)
            timestamp = uint64(time.time())

            spend_bundle = SpendBundle.aggregate(self._spend_bundles)
            self._spend_bundles = []

            pool_public_key = get_pool_public_key()
            plot_public_key = get_plot_public_key()

            pos = ProofOfSpace(pool_public_key, plot_public_key)
            coinbase_coin, coinbase_signature = create_coinbase_coin_and_signature(
                block_number, coinbase_puzzle_hash, REWARD, pool_public_key)

            header, body = farm_new_block(
                self._chain_view.tip_hash, block_number, pos, spend_bundle, coinbase_coin,
                coinbase_signature, fees_puzzle_hash, timestamp)

            header_signature = sign_header(header, plot_public_key)

            [await self._storage.add_preimage(_.as_bin()) for _ in (header, body)]

            chain_view = await self._chain_view.augment_chain_view(
                header, header_signature, self._storage, self._storage, REWARD)

            self._chain_view = chain_view

            self._block_index += 1
            self._tip = HeaderHash(header)

        return dict(header=header, body=body)

    async def do_all_unspents(self, **kwargs):
        all_unspents = [_[0] async for _ in self._storage.all_unspents()]
        return dict(unspents=all_unspents)

    async def do_hash_preimage(self, id):
        r = await self._storage.hash_preimage(id)
        return r


"""
Copyright 2019 Chia Network Inc

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
