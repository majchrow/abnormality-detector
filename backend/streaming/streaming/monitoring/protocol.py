"""Communication with worker processes over system pipes."""
# TODO:
#  - it would be nice not to send dictionaries, but how?
#  - msgpack? protobuf?
#  - subprocess doesn't have access to this module anyway (PYTHONPATH)
import json


def serialize(payload: dict):
    return (json.dumps(payload) + '\n').encode()


class AsyncStreams:
    @staticmethod
    async def send_str(s: str, stream):
        stream.write((s + '\n').encode())
        await stream.drain()

    @staticmethod
    async def send_dict(payload: dict, stream):
        data = serialize(payload)
        stream.write(data)
        await stream.drain()

    @staticmethod
    async def read_str(stream):
        return (await stream.readline()).decode()
