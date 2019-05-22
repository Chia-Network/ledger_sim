import asyncio
import logging
import struct

import cbor


async def reader_to_cbor_event_stream(dict_with_reader):
    """
    Turn a reader into a generator that yields events with cbor messages.
    """

    template = dict(dict_with_reader)
    reader = dict_with_reader["reader"]
    while True:
        try:
            message_size_blob = await reader.readexactly(2)
            message_size, = struct.unpack(">H", message_size_blob)
            blob = await reader.readexactly(message_size)
            message = cbor.loads(blob)

            new_dict = dict(template)
            new_dict.update(message=message)
            yield new_dict
        except asyncio.IncompleteReadError:
            break
        except ValueError:
            logging.info("badly formatted cbor from stream %s", reader)
            break

    if "writer" in dict_with_reader:
        dict_with_reader["writer"].close()


def send_cbor_message(msg, writer):
    msg_blob = cbor.dumps(msg)
    length_blob = struct.pack(">H", len(msg_blob))
    writer.write(length_blob)
    writer.write(msg_blob)


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
