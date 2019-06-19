import logging

from .utils.server import readers_writers_server_for_port
from .utils.cbor_messages import reader_to_cbor_stream, send_cbor_message
from .utils.event_stream import rws_to_event_aiter


async def api_server(port, api):
    rws_aiter = readers_writers_server_for_port(port)
    event_aiter = rws_to_event_aiter(rws_aiter, reader_to_cbor_stream)

    async for event in event_aiter:
        try:
            # {"c": "command"}
            message = event["message"]
            c = message.get("c")
            f = getattr(api, "do_%s" % c, None)
            if f:
                r = await f(message)
                logging.debug("handled %s message" % c)
            else:
                r = dict(error="Missing or invalid command: %s" % c)
                logging.error("failure in %s message" % c)
        except Exception as ex:
            logging.exception("failure in %s message" % c)
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
