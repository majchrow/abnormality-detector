import asyncio
import logging

import websockets
from websockets import WebSocketServerProtocol

from utils import enable_logger


class Server:
    def __init__(self, FLAGS):
        self.FLAGS = FLAGS
        self.clients = set()
        enable_logger(directory="logs/server", filename="server")
        self._start_websocket()

    def _start_websocket(self) -> None:
        start_server = websockets.serve(self.ws_handler, self.FLAGS.host, self.FLAGS.port)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(start_server)
        logging.info(f"Websocket server listening on port {self.FLAGS.host}:{self.FLAGS.port}.")
        loop.run_forever()

    async def ws_handler(self, ws: WebSocketServerProtocol, url: str) -> None:
        await self.register(ws)

    async def register(self, ws: WebSocketServerProtocol) -> None:
        self.clients.add(ws)
        logging.info(f"{ws.remote_address} connected.")

    async def unregister(self, ws: WebSocketServerProtocol) -> None:
        self.clients.remove(ws)
        logging.info(f"{ws.remote_address} disconnected.")
