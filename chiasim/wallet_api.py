import datetime
import logging

from .hashable import SpendBundle

from .farming import Mempool


class WalletAPI:
    def __init__(self):
        self._mempool = Mempool()

    async def do_ping(self, message):
        logging.info("ping")
        return dict(response="got ping message %r at time %s" % (
            message.get("m"), datetime.datetime.utcnow()))

    async def do_push_tx(self, message):
        logging.info("push_tx %s", message)
        tx_blob = message.get("tx")
        spend_bundle = SpendBundle.from_bin(tx_blob)
        self._mempool.accept_spend_bundle(spend_bundle)


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
