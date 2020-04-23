import asyncio
import logging

from websockets import WebSocketServerProtocol, serve

from utils import enable_logger


class Server:
    def __init__(self, FLAGS) -> None:
        self.FLAGS = FLAGS
        self.clients = set()
        enable_logger(directory="logs/server", filename="server")

    def start(self) -> None:
        start_server = serve(self.ws_handler, self.FLAGS.host, self.FLAGS.port)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(start_server)
        logging.info(f"Websocket server listening on port {self.FLAGS.host}:{self.FLAGS.port}.")
        loop.run_forever()

    async def ws_handler(self, ws: WebSocketServerProtocol, url: str) -> None:
        await self.register(ws)
        try:
            await self.request_handler(ws)
        finally:
            await self.unregister(ws)

    async def register(self, ws: WebSocketServerProtocol) -> None:
        self.clients.add(ws)
        logging.info(f"{ws.remote_address} connected.")

    async def unregister(self, ws: WebSocketServerProtocol) -> None:
        self.clients.remove(ws)
        logging.info(f"{ws.remote_address} disconnected.")

    async def request_handler(self, ws: WebSocketServerProtocol) -> None:
        msg = await ws.recv()
        print(f"Received {msg}")
        await ws.send("hello from server")
