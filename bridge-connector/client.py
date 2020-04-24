import asyncio
import json

from websockets import connect

from utils import enable_logger


class Client:
    def __init__(self, FLAGS) -> None:
        self.FLAGS = FLAGS
        enable_logger(directory="logs/client", filename="client")

    def start(self) -> None:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._connect_to_websocket())
        loop.run_until_complete()

    async def subscribe(self, ws):
        subscribe_msg = {"type": "message",
                         "message":
                             {"messageId": 9,
                              "type": "subscribeRequest",
                              "subscriptions":
                                  [{"index": 1,
                                    "type": "callRoster",
                                    "call": "2c62fcd9-ec14-40c1-8608-847ea30fb13f",
                                    "elements": ["name", "uri", "state", "audioMuted", "videoMuted", "importance", "layout", "activeSpeaker", "presenter"]},
                                    {"index": 2,
                                     "type": "callInfo",
                                     "call": "2c62fcd9-ec14-40c1-8608-847ea30fb13f",
                                    "elements": ["name", "participants", "recording", "streaming"]
                                     }]}}
        print(subscribe_msg)
        await ws.send(json.dumps(subscribe_msg))

    async def send_ack(self, message_id, ws):
        msg = {"type":"messageAck",
               "messageAck":
                   {"messageId": message_id,
                    "status":"success"}}
        ws.send(json.dumps(msg))

    @staticmethod
    def save_to_file(msg):
        with open("messages.txt", "w") as file:
            file.write(msg)

    async def recv_msg(self, ws):
        while True:
            msg = await ws.recv()
            msg_dict = json.loads(msg)
            msg_id = msg_dict["message"]["messageId"]
            self.save_to_file(msg)
            await self.send_ack(msg_id, ws)

    async def _connect_to_websocket(self) -> None:
        uri = f"ws://{self.FLAGS.host}:{self.FLAGS.port}"
        async with connect(uri) as ws:
            await self.subscribe(ws)
            await self.recv_msg(ws)

