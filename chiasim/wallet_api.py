import datetime
import logging

from .farming import Mempool
from .hashable import BLSSignature, Coin, ProgramHash, ProofOfSpace, SpendBundle


class WalletAPI:
    def __init__(self, block_tip, storage):
        self._mempool = Mempool(block_tip, storage)
        self._storage = storage

    async def do_ping(self, message):
        logging.info("ping")
        return dict(response="got ping message %r at time %s" % (
            message.get("m"), datetime.datetime.utcnow()))

    async def do_push_tx(self, message):
        logging.info("push_tx %s", message)
        tx_blob = message.get("tx")
        spend_bundle = SpendBundle.from_bin(tx_blob)
        if not spend_bundle.validate_signature():
            raise ValueError("bad signature on %s" % spend_bundle)

        # TODO: uncomment this
        # await self._mempool.validate_spend_bundle(spend_bundle)

        self._mempool.accept_spend_bundle(spend_bundle)
        return dict(response="accepted %s" % spend_bundle)

    async def do_farm_block(self, message):
        logging.info("farm_block")
        block_number = self._mempool.next_block_number()
        proof_of_space = ProofOfSpace.from_bin(message.get("pos"))

        coinbase_coin = Coin.from_bin(message.get("coinbase_coin"))
        coinbase_signature = BLSSignature.from_bin(message.get("coinbase_signature"))

        fees_puzzle_hash = ProgramHash.from_bin(message.get("fees_puzzle_hash"))

        logging.info("coinbase_coin: %s", coinbase_coin)
        logging.info("fees_puzzle_hash: %s", fees_puzzle_hash)

        header, body, additions, removals = self._mempool.farm_new_block(
            block_number, proof_of_space, coinbase_coin, coinbase_signature, fees_puzzle_hash)

        await self._mempool.accept_new_block(block_number, additions, removals)

        return dict(
            header=header.as_bin(), body=body.as_bin())


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
