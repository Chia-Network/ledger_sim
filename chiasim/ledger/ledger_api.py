import datetime
import logging
import time

from chiasim.atoms import uint64
from chiasim.farming import farm_new_block
from chiasim.hashable import (
    BLSSignature, Coin, HeaderHash,
    ProgramHash, ProofOfSpace, SpendBundle
)
from chiasim.remote.api_decorators import api_request

log = logging.getLogger(__name__)


class LedgerAPI:
    def __init__(self, block_tip: HeaderHash, block_index: uint64, storage):
        self._tip = block_tip
        self._block_index = block_index
        self._storage = storage
        self._spend_bundles = []

    async def do_ping(self, m=None):
        log.info("ping")
        return dict(response="got ping message %r at time %s" % (
            m, datetime.datetime.utcnow()))

    @api_request(tx=SpendBundle.from_bin)
    async def do_push_tx(self, tx):
        log.info("push_tx %s", tx)
        if not tx.validate_signature():
            raise ValueError("bad signature on %s" % tx)

        self._spend_bundles.append(tx)
        return dict(response="accepted %s" % tx)

    @api_request(
        pos=ProofOfSpace.from_bin,
        coinbase_coin=Coin.from_bin,
        coinbase_signature=BLSSignature.from_bin,
        fees_puzzle_hash=ProgramHash.from_bin
    )
    async def do_farm_block(self, pos, coinbase_coin, coinbase_signature, fees_puzzle_hash):
        block_number = self._block_index

        log.info("farm_block")
        log.info("coinbase_coin: %s", coinbase_coin)
        log.info("fees_puzzle_hash: %s", fees_puzzle_hash)

        timestamp = uint64(time.time())

        spend_bundle = SpendBundle.aggregate(self._spend_bundles)
        self._spend_bundles = []

        header, body = farm_new_block(
            self._tip, block_number, pos, spend_bundle, coinbase_coin,
            coinbase_signature, fees_puzzle_hash, timestamp)

        self._block_index += 1
        self._tip = HeaderHash(header)

        return dict(header=header, body=body)

    async def do_all_unspents(self, **kwargs):
        all_unspents = [_[0] async for _ in self._storage.all_unspents()]
        return dict(unspents=all_unspents)


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
