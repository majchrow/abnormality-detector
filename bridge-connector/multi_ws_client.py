import asyncio
import json
import logging
import os
from datetime import datetime
from enum import Enum

import requests
from websockets import connect

from utils import enable_logger

# Server communication
calls_subscription = {
    "index": 3,
    "type": "calls",
    "elements": [
        "name", "participants", "distributedInstances", "recording", "endpointRecording", "streaming", "lockState",
        "callType", "callCorrelator"
    ]
}


def get_call_info_subscription(call):
    return {"index": 2,
            "type": "callInfo",
            "call": call,
            "elements": ["name", "participants", "distributedInstances", "recording",
                         "endpointRecording", "streaming", "lockState", "callType",
                         "callCorrelator", "joinAudioMuteOverride"]
            }


def get_call_roster_subscription(call):
    return {"index": 1,
            "type": "callRoster",
            "call": call,
            "elements": ["name", "uri", "state", "direction", "audioMuted", "videoMuted",
                         "importance", "layout", "activeSpeaker", "presenter",
                         "endpointRecording", "canMove", "movedParticipant",
                         "movedParticipantCallBridge"]}


def get_subscription_request(subscriptions, message_id):
    return {"type": "message",
            "message":
                {"messageId": message_id,
                 "type": "subscribeRequest",
                 "subscriptions": subscriptions
                 }}


def get_ack(message_id):
    return {"type": "messageAck",
            "messageAck":
                {"messageId": message_id,
                 "status": "success"}}


class CallState(Enum):
    CONNECTED = 'CONNECTED'
    PENDING = 'PENDING'


class Call:
    def __init__(self, call_id, state):
        self.call_id = call_id
        self.state = state
        self.handler = None
        self.servers = set()

    @property
    def active(self):
        return self.state == CallState.CONNECTED

    def add(self, server):
        if self.active:
            # Some server endpoint is handling it already
            self.servers.add(server)
        elif server.available:
            self.state = CallState.CONNECTED
            self.handler = server
            server.on_handle_call(self.call_id)
        else:
            self.servers.add(server)

    def remove(self, server):
        if server == self.handler:
            # We need a new handler if we can find any
            for s in self.servers:
                if s.available:
                    self.handler = s
                    self.handler.on_handle_call(self.call_id)
            else:
                self.handler = None
                self.state = CallState.PENDING
        else:
            self.servers.remove(server)


class Connector:
    def __init__(self, config):
        self.addresses = config.addresses
        self.logfile = config.logfile
        self.servers = [ServerEndpoint(addr, self, config.max_ws_count) for addr in self.addresses]
        self.calls = {}

    def on_calls_change(self, call_id, update_type, server_endpoint):
        method_name = f'on_{update_type}_call'
        try:
            method = getattr(self, method_name)
            method(call_id, server_endpoint)
        except AttributeError:
            pass  # TODO: log error

    def on_add_call(self, call_id, server_endpoint):
        if call_id not in self.calls:
            self.calls[call_id] = Call(call_id=call_id, state=CallState.PENDING)
        self.calls[call_id].add(server_endpoint)

    def on_update_call(self, call_id, server_endpoint):
        pass  # TODO: don't know yet, maybe when call becomes distributed??

    def on_remove_call(self, call_id, server_endpoint):
        if call_id in self.calls:
            self.calls[call_id].remove(server_endpoint)


class ServerEndpoint:
    def __init__(self, address, global_state, max_ws_count):
        self.host, self.port = address
        self.global_state = global_state
        self.max_ws_count = max_ws_count
        self.sockets = {}
        self.auth_token = None
        self.message_id = None

        # TODO: logging could be async too
        enable_logger(directory="logs/client", filename="client")

    @property
    def available(self):
        return len(self.sockets) < self.max_ws_count

    def start(self) -> None:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._connect_to_websocket())

    async def refresh_client(self):
        self.message_id = 0
        self._refresh_auth_token()
        await asyncio.sleep(2)

    def _refresh_auth_token(self):
        try:
            url = f"https://{self.host}:{self.port}/api/v1/authTokens"
            # TODO: this request could be async too
            response = requests.post(url, data={}, auth=(os.environ["BRIDGE_USERNAME"], os.environ["BRIDGE_PASSWORD"]))
            self.auth_token = response.headers["X-Cisco-CMS-Auth-Token"]
        except Exception as e:
            logging.error(e)

    async def calls_subscribe(self, ws):
        request = get_subscription_request(calls_subscription, self.message_id)
        await ws.send(json.dumps(request))

    @staticmethod
    async def call_subscribe(call_id, ws):
        call_info = get_call_info_subscription(call_id)
        await ws.send(json.dumps(call_info))
        call_roster = get_call_roster_subscription(call_id)
        await ws.send(json.dumps(call_roster))

    @staticmethod
    async def acknowledge(msg_id, ws):
        await ws.send(json.dumps(get_ack(msg_id)))

    def on_handle_call(self, call_id):
        pass  # TODO: create new WS if already handling one, else just subscribe

    async def process_message(self, msg_dict, ws):
        # TODO: acknowledge & save to file if necessary
        try:
            # note: could also be "messageAck" - we ignore it
            if msg_dict["type"] == "message":
                msg_type = msg_dict["message"]["type"]
                if "callListUpdate" in msg_type:
                    updates = msg_dict["message"]["updates"]
                    for update in updates:
                        call_id = update["call"]
                        update_type = update["updateType"]
                        self.global_state.on_calls_change(call_id, update_type, self)
                elif "callInfoUpdate" in msg_type or "rosterUpdate" in msg_type:
                    # TODO: it must be event for this socket but check it anyway
                    self.save_to_file(msg_dict)
                return msg_dict["message"]["messageId"]
        except Exception as e:
            logging.error(e)
        return None

    # TODO: either log or saving to file?
    def save_to_file(self, msg_dict):
        msg_dict['date'] = datetime.now().isoformat()
        with open(self.logfile, "a") as file:
            json.dump(msg_dict, file, indent=4)
            file.write(",\n")

    async def recv_msg(self, ws):
        while True:
            msg = await ws.recv()
            msg_dict = json.loads(msg)
            await self.process_message(msg_dict, ws)

    async def _connect_to_websocket(self) -> None:
        while True:
            try:
                await self.refresh_client()
                if self.auth_token:
                    uri = f"wss://{self.host}:{self.port}/events/v1?authToken={self.auth_token}"
                    # noinspection PyTypeChecker
                    async with connect(uri, ping_timeout=None) as ws:
                        await self.calls_subscribe(ws)
                        await self.recv_msg(ws)
            except Exception as e:
                logging.error(e)
