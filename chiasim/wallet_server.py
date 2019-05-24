import datetime
import logging

from aiter import join_aiters, map_aiter

from .utils.server import readers_writers_server_for_port
from .utils.cbor_wrap import reader_to_cbor_event_stream, send_cbor_message


async def do_ping(message):
    return dict(response="got ping message %r at time %s" % (message.get("m"), datetime.datetime.utcnow()))


async def do_create_new_block(message):
    pass


async def wallet_server(port):
    rws_aiter = readers_writers_server_for_port(port)
    event_aiter = join_aiters(map_aiter(reader_to_cbor_event_stream, rws_aiter))

    async for event in event_aiter:
        try:
            # {"c": "command"}
            message = event["message"]
            c = message.get("c")
            f = globals().get("do_%s" % c)
            if f:
                r = await f(message)
                logging.debug("handled %s message" % c)
            else:
                r = dict(error="Missing or invalid command: %s" % c)
                logging.error("failure in %s message" % c)
        except Exception as ex:
            r = dict(error="exception: %s" % ex)
        send_cbor_message(r, event["writer"])


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
