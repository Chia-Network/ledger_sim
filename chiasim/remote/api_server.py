import logging

from aiter import map_aiter, parallel_map_aiter

from ..utils.cbor_messages import reader_to_cbor_stream, send_cbor_message
from ..utils.event_stream import rws_to_event_aiter

log = logging.getLogger(__name__)


async def event_to_response(event):
    return event["message"]


async def api_server(rws_aiter, api, workers=1):
    event_aiter = rws_to_event_aiter(rws_aiter, reader_to_cbor_stream)

    response_writer_for_event = make_response_map_for_api(api)

    if workers > 1:
        response_writer_aiter = parallel_map_aiter(response_writer_for_event, workers, event_aiter)
    else:
        response_writer_aiter = map_aiter(response_writer_for_event, event_aiter)

    async for response, writer in response_writer_aiter:
        if response is not None:
            send_cbor_message(response, writer)


def make_response_map_for_api(api):

    async def response_for_message(message):
        try:
            # {"c": "command"}
            c = message.get("c")
            nonce = message.get("n")
            f = getattr(api, "do_%s" % c, None)
            if f:
                args = message.get("q", {})
                r = await f(**args)
                log.debug("handled %s message" % c)
                d = dict(r=r)
            else:
                d = dict(e="Missing or invalid command: %s" % c)
                log.error("failure in %s message" % c)
        except Exception as ex:
            log.exception("failure in %s message" % c)
            d = dict(e="exception: %s" % ex)
        if nonce is None:
            return None
        d["n"] = nonce
        return d

    async def response_writer_for_event(event):
        message = event["message"]
        response = await response_for_message(message)
        return response, event["writer"]

    return response_writer_for_event


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
