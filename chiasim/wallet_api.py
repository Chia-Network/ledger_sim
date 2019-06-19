import datetime
import logging

from .hashable import ProofOfSpace, SpendBundle

from .farming import Mempool


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
            return dict(response="bad signature on %s" % spend_bundle)
        self._mempool.accept_spend_bundle(spend_bundle)
        return dict(response="accepted %s" % spend_bundle)

    async def do_farm_block(self, message):
        from .hashable import Program
        from tests.helpers import PUBLIC_KEYS, PRIVATE_KEYS, make_simple_puzzle_program
        from tests.test_farmblock import fake_proof_of_space, make_coinbase_coin_and_signature

        logging.info("farm_block %s", message)
        block_number = self._mempool.next_block_number()
        pos_blob = message.get("pos")
        if pos_blob is None:
            proof_of_space = fake_proof_of_space()
        else:
            proof_of_space = ProofOfSpace.from_bin(pos_blob)

        pool_private_key = PRIVATE_KEYS[0]
        puzzle_program = make_simple_puzzle_program(PUBLIC_KEYS[1])
        coinbase_coin, coinbase_signature = make_coinbase_coin_and_signature(
            block_number, puzzle_program, pool_private_key)
        fees_puzzle_program = Program(make_simple_puzzle_program(PUBLIC_KEYS[2]))

        header, body, additions, removals = self._mempool.farm_new_block(
            block_number, proof_of_space, coinbase_coin, coinbase_signature, fees_puzzle_program)
        return dict(header=header.as_bin(), body=body.as_bin())


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
