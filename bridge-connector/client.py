import asyncio
import json
import logging
import os
import time
from datetime import datetime

import requests
from websockets import connect

from utils import enable_logger

INIT_SUBSCRIPTION = {
    "index": 3,
    "type": "calls",
    "elements": [
        "name", "participants", "distributedInstances", "recording", "endpointRecording", "streaming", "lockState",
        "callType", "callCorrelator"
    ]
}


class Client:
    def __init__(self, FLAGS) -> None:
        self.FLAGS = FLAGS
        self.message_id = None
        self.calls = None
        self.subscriptions = None
        self.auth_token = None
        self.refresh_client()
        enable_logger(directory="logs/client", filename="client")

    def start(self) -> None:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._connect_to_websocket())
        loop.run_until_complete()

    def refresh_client(self):
        self.message_id = 0
        self.calls = set()
        self.subscriptions = [INIT_SUBSCRIPTION]
        self._refresh_auth_token()
        time.sleep(2)

    def _refresh_auth_token(self):
        try:
            url = f"https://{self.FLAGS.host}:{self.FLAGS.port}/api/v1/authTokens"
            response = requests.post(url, data={}, auth=(os.environ["BRIDGE_USERNAME"], os.environ["BRIDGE_PASSWORD"]))
            self.auth_token = response.headers["X-Cisco-CMS-Auth-Token"]
        except Exception as e:
            logging.error(e)

    @staticmethod
    def get_call_info_subscription(call):
        return {"index": 2,
                "type": "callInfo",
                "call": call,
                "elements": ["name", "participants", "distributedInstances", "recording",
                             "endpointRecording", "streaming", "lockState", "callType",
                             "callCorrelator", "joinAudioMuteOverride"]
                }

    @staticmethod
    def get_call_roster_subscription(call):
        return {"index": 1,
                "type": "callRoster",
                "call": call,
                "elements": ["name", "uri", "state", "direction", "audioMuted", "videoMuted",
                             "importance", "layout", "activeSpeaker", "presenter",
                             "endpointRecording", "canMove", "movedParticipant",
                             "movedParticipantCallBridge"]}

    def update_subscriptions(self, call):
        call_info = self.get_call_info_subscription(call)
        call_roster = self.get_call_roster_subscription(call)
        self.subscriptions.append(call_roster)
        self.subscriptions.append(call_info)

    def get_subscription_request(self):
        self.message_id = self.message_id + 1
        return {"type": "message",
                "message":
                    {"messageId": self.message_id,
                     "type": "subscribeRequest",
                     "subscriptions": self.subscriptions
                     }}

    async def subscribe(self, ws):
        await ws.send(json.dumps(self.get_subscription_request()))

    async def send_ack(self, message_id, ws):
        msg = {"type": "messageAck",
               "messageAck":
                   {"messageId": message_id,
                    "status": "success"}}
        await ws.send(json.dumps(msg))

    async def process_message(self, msg_dict, ws):
        try:
            if msg_dict["type"] == "message":
                msg_type = msg_dict["message"]["type"]
                if "callListUpdate" in msg_type:
                    updates = msg_dict["message"]["updates"]
                    for update in updates:
                        call = update["call"]
                        if call in self.calls:
                            continue
                        self.calls.add(call)
                        self.update_subscriptions(call)
                        await self.subscribe(ws)
                return msg_dict["message"]["messageId"]
        except Exception as e:
            logging.error(e)
        return None

    def save_to_file(self, msg_dict):
        msg_dict['date'] = datetime.now().isoformat()
        with open(self.FLAGS.logfile, "a") as file:
            json.dump(msg_dict, file, indent=4)
            file.write(",\n")

    async def recv_msg(self, ws):
        while True:
            msg = await ws.recv()
            msg_dict = json.loads(msg)
            msg_id = await self.process_message(msg_dict, ws)
            self.save_to_file(msg_dict)
            if msg_id:
                await self.send_ack(msg_id, ws)

    async def _connect_to_websocket(self) -> None:
        while True:
            try:
                if self.auth_token:
                    uri = f"wss://{self.FLAGS.host}:{self.FLAGS.port}/events/v1?authToken={self.auth_token}"
                    async with connect(uri, ping_timeout=None) as ws:
                        await self.subscribe(ws)
                        await self.recv_msg(ws)
                else:
                    self.refresh_client()
            except Exception as e:
                logging.error(e)
                self.refresh_client()
