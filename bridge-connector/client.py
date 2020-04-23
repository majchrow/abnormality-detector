import asyncio

from websockets import connect

from utils import enable_logger


class Client:
    def __init__(self, FLAGS) -> None:
        self.FLAGS = FLAGS
        enable_logger(directory="logs/client", filename="client")

    def start(self) -> None:
        asyncio.get_event_loop().run_until_complete(self._connect_to_websocket())

    async def _connect_to_websocket(self) -> None:
        uri = f"ws://{self.FLAGS.host}:{self.FLAGS.port}"
        async with connect(uri) as ws:
            await ws.send("hello from client")
            msg = await ws.recv()
            print(f"Received {msg}")
