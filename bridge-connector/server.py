import asyncio
import json
import logging
from time import sleep

from websockets import WebSocketServerProtocol, serve

from utils import enable_logger


class Server:
    def __init__(self, FLAGS) -> None:
        self.FLAGS = FLAGS
        self.clients = set()
        self.call_info_clients = []
        self.call_roaster_clients = []
        self.calls_clients = []
        self.call_info_data = []
        self.call_roaster_data = []
        self.calls_data = []
        self.unknown = []
        self.loop = None
        enable_logger(directory="logs/server", filename="server")
        self._prepare_data()

    def start(self) -> None:
        start_server = serve(self.ws_handler, self.FLAGS.host, self.FLAGS.port)
        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(start_server)
        logging.info(f"Websocket server listening on port {self.FLAGS.host}:{self.FLAGS.port}.")
        sleep(3)
        self.start_streams()
        self.loop.run_forever()

    def _prepare_data(self) -> None:
        with open(self.FLAGS.logfile) as json_file:
            data = json.load(json_file)
        for message in data:
            queue = self.unknown
            if message['message']['type'] == "rosterUpdate":
                queue = self.call_roaster_data
            elif message['message']['type'] == "callInfoUpdate":
                queue = self.call_info_data
            elif message['message']['type'] == "callListUpdate":
                queue = self.calls_data
            queue.append(message)

    async def ws_handler(self, ws: WebSocketServerProtocol, url: str) -> None:
        await self.register(ws)
        await self.handler(ws)

    async def register(self, ws: WebSocketServerProtocol) -> None:
        self.clients.add(ws)
        logging.info(f"{ws.remote_address} connected.")

    async def unregister(self, ws: WebSocketServerProtocol) -> None:
        self.clients.remove(ws)
        logging.info(f"{ws.remote_address} disconnected.")

    def start_streams(self) -> None:
        self.loop.create_task(self.stream_call_info())
        self.loop.create_task(self.stream_call_roaster())
        self.loop.create_task(self.stream_calls())

    async def handler(self, ws: WebSocketServerProtocol) -> None:
        while True:
            msg = await ws.recv()
            await self._parse_message(ws, msg)
            logging.info(f"Got from {ws} message {msg}")

    async def _parse_message(self, ws: WebSocketServerProtocol, msg: str) -> None:
        try:
            msg_parsed = json.loads(msg)['message']
            if msg_parsed['type'] == "subscribeRequest":
                subscriptions = msg_parsed['subscriptions']
                for subscription in subscriptions:
                    if subscription['type'] == "callRoster":
                        self.call_roaster_clients.append(ws)
                    elif subscription['type'] == "callInfo":
                        self.call_info_data.append(ws)
                    else:
                        self.calls_data.append(ws)
        except:
            logging.info(msg)

    async def stream_call_info(self) -> None:
        for data in self.call_info_data:
            logging.info(data)
            for client in self.call_info_clients:
                await client.send(json.dumps(data))
            await asyncio.sleep(2)

    async def stream_call_roaster(self) -> None:
        for data in self.call_roaster_data:
            logging.info(data)
            for client in self.call_roaster_clients:
                await client.send(json.dumps(data))
            await asyncio.sleep(2)

    async def stream_calls(self) -> None:
        for data in self.calls_data:
            logging.info(data)
            for client in self.calls_clients:
                await client.send(json.dumps(data))
            await asyncio.sleep(2)
