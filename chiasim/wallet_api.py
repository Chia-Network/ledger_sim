import datetime
import logging

from .api_decorators import api_request
from .farming import Mempool
from .hashable import BLSSignature, Coin, ProgramHash, ProofOfSpace, SpendBundle


class WalletAPI:
    def __init__(self, block_tip, storage):
        self._mempool = Mempool(block_tip, storage)
        self._storage = storage

    async def do_ping(self, **message):
        logging.info("ping")
        return dict(response="got ping message %r at time %s" % (
            message.get("m"), datetime.datetime.utcnow()))

    @api_request(tx=SpendBundle.from_bin)
    async def do_push_tx(self, tx, **kwargs):
        logging.info("push_tx %s", tx)
        if not tx.validate_signature():
            raise ValueError("bad signature on %s" % tx)

        await self._mempool.validate_spend_bundle(tx)

        self._mempool.accept_spend_bundle(tx)
        return dict(response="accepted %s" % tx)

    @api_request(
        pos=ProofOfSpace.from_bin,
        coinbase_coin=Coin.from_bin,
        coinbase_signature=BLSSignature.from_bin,
        fees_puzzle_hash=ProgramHash.from_bin
    )
    async def do_farm_block(self, pos, coinbase_coin, coinbase_signature, fees_puzzle_hash, **message):
        block_number = self._mempool.next_block_index()

        logging.info("farm_block")
        logging.info("coinbase_coin: %s", coinbase_coin)
        logging.info("fees_puzzle_hash: %s", fees_puzzle_hash)

        header, body, additions, removals = self._mempool.farm_new_block(
            block_number, pos, coinbase_coin, coinbase_signature, fees_puzzle_hash)

        await self._mempool.accept_new_block(block_number, additions, removals)

        return dict(
            header=header.as_bin(), body=body.as_bin())

    async def do_all_unspents(self, **kwargs):
        all_unspents = [_[0].as_bin() async for _ in self._storage.all_unspents()]
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
