from chiasim.api_decorators import transform_args
from chiasim.remote.meta import make_proxy
from chiasim.utils.cbor_messages import reader_to_cbor_stream, send_cbor_message


async def invoke_remote(method, remote, *args, **kwargs):
    """
    Send the given message to the remote and return the transformed
    response.
    """
    reader, writer = remote.get("reader"), remote.get("writer")
    msg = dict(c=method)
    msg.update(kwargs)
    send_cbor_message(msg, writer)
    await writer.drain()

    transformation = remote.get("signatures", {}).get(method)
    return await accept_response(reader, transformation)


async def accept_response(reader, transformation):
    """
    This is a hack to get the first message out of the reader stream
    and transform it.
    """
    async for _ in reader_to_cbor_stream(reader):
        break
    if transformation:
        _ = transform_args(transformation, _)
    return _


def request_response_proxy(reader, writer, remote_signatures={}):
    """
    Create a proxy object that handles request/response for the given remote.
    You can optionally pass in signatures for automatic conversion of key
    values from bytes (or other cbor objects) to specific types.
    """
    d = dict(reader=reader, writer=writer, signatures=remote_signatures)
    return make_proxy(invoke_remote, d)
