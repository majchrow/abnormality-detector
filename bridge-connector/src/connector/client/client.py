import aiohttp
import json
import logging
from aiohttp import ClientConnectionError
from dataclasses import dataclass
from typing import Optional
from websockets import connect

from .protocol import (
    ack, calls_subscription, call_info_subscription, call_roster_subscription,subscription_request
)


@dataclass
class Call:
    name: str
    id: str
    ci_subscription_index: Optional[int]


class Client:

    TAG = 'Client'

    def __init__(self, host: str, port: int, ssl: bool, call_manager):
        self.host = host
        self.port = port
        self.ssl = ssl
        self.TAG += f' {host}:{port}'

        self.call_manager = call_manager
        self.auth_token = None
        self.ws = None

        self.message_id = 0

        # How it works:
        #  - we get call ID and name of new call -> we generate subscription index for this call
        #  - then we obtain a message from the server and:
        #    - for callListUpdate the only thing we ALWAYS get is call ID
        #    - for callInfoUpdate and rosterUpdate we always get subscription index
        #  - hence, when we receive:
        #    - callListUpdate, from call ID we obtain call name
        #    - callInfoUpdate or rosterUpdate, from subscription index we get call ID and call name
        #  - we add this info to the message if necessary
        self.subscription_ind = 2
        self.subscriptions = {}         # subscription index -> Call
        self.calls = {}                 # call name -> Call
        self.call_ids = {}              # call ID -> Call

    @property
    def token_uri(self):
        if self.ssl:
            return f'https://{self.host}:{self.port}/api/v1/authTokens'
        else:
            return f'http://{self.host}:{self.port}/api/v1/authTokens'

    @property
    def event_uri(self):
        if self.ssl:
            return f'wss://{self.host}:{self.port}/events/v1?authToken={self.auth_token}'
        else:
            return f'ws://{self.host}:{self.port}/events/v1?authToken={self.auth_token}'

    async def run(self, login: str, password: str, session: aiohttp.ClientSession):
        auth = aiohttp.BasicAuth(login, password)

        async with session.post(self.token_uri, data={}, auth=auth) as response:
            try:
                self.auth_token = response.headers["X-Cisco-CMS-Auth-Token"]
            except KeyError:
                raise ClientConnectionError('X-Cisco-CMS-Auth-Token missing from response headers')

        # noinspection PyTypeChecker
        async with connect(self.event_uri, ping_interval=None) as ws:
            self.ws = ws
            await self._subscribe()

            while True:
                msg = await ws.recv()
                msg_dict = json.loads(msg)
                msg_id = await self.process_message(msg_dict)
                if msg_id:
                    await ws.send(json.dumps(ack(msg_id)))  # acknowledge

    async def process_message(self, msg_dict):
        logging.info(f'{self.TAG}: RECV {msg_dict}')

        # note: could also be "messageAck" - we ignore it
        if msg_dict["type"] != "message":
            return

        msg_type = msg_dict["message"]["type"]
        if msg_type == "callListUpdate":
            await self.on_call_list_update(msg_dict)
        elif msg_type == "callInfoUpdate" or msg_type == "rosterUpdate":
            index = msg_dict["message"]["subscriptionIndex"]
            if index in self.subscriptions:
                if msg_type == 'callInfoUpdate':
                    await self.on_call_info_update(msg_dict)
                else:
                    await self.on_roster_update(msg_dict)
            else:
                logging.warning(f'{self.TAG}: received update after "remove": {msg_dict}')
        elif "subscriptionUpdate" in msg_type:
            pass
        else:
            logging.warning(f'{self.TAG}: unknown message type {msg_type}')
            return

        return msg_dict["message"]["messageId"]

    async def on_call_list_update(self, msg: dict):
        # Add call name to "update" and "remove" messages (they only have call ID)
        updates = msg["message"]["updates"]
        for update in updates:
            update_type = update["updateType"]
            call_id = update["call"]

            if update_type == 'add':
                call_name = update["name"]
                call = Call(name=call_name, id=call_id, ci_subscription_index=None)
                self.calls[call_name] = self.call_ids[call_id] = call
            else:
                call_name = self.call_ids[call_id].name
                update['name'] = call_name

        await self.call_manager.on_call_list_update(msg, self)

    async def on_call_info_update(self, msg: dict):
        # Add call name and call ID (only "add" has name)
        index = msg["message"]["subscriptionIndex"]
        call = self.subscriptions[index]
        msg["message"]["callInfo"]["call"] = call.id
        msg["message"]["callInfo"]["name"] = call.name
        await self.call_manager.on_call_info_update(msg, call.name)

    async def on_roster_update(self, msg: dict):
        # Add call name and call ID
        index = msg["message"]["subscriptionIndex"]
        call = self.subscriptions[index]
        msg["call"] = call.id
        msg["name"] = call.name
        await self.call_manager.on_roster_update(msg, call.name)

    async def on_connect_to(self, call_name):
        # Setup subscription indexes for call info and roster info
        s_ind = self.subscription_ind
        self.subscription_ind += 2

        call = self.calls[call_name]
        call.ci_subscription_index = s_ind
        self.subscriptions[s_ind] = self.subscriptions[s_ind + 1] = call

        # Send server subscription
        await self._subscribe()
        logging.info(f'{self.TAG}: subscribed to call {call.name} with ID {call.id}')

    async def on_disconnect_from(self, call_name):
        call = self.calls[call_name]
        s_ind = call.ci_subscription_index

        del self.subscriptions[s_ind]
        del self.subscriptions[s_ind + 1]
        del self.calls[call_name]
        del self.call_ids[call.id]

        logging.info(f'{self.TAG}: removed call {call_name} with ID {call.id}')

    async def _subscribe(self):
        subscriptions = [calls_subscription]

        for call_id, call in self.call_ids.items():
            if call.ci_subscription_index is not None:
                subscriptions.extend([
                    call_info_subscription(call_id, call.ci_subscription_index),
                    call_roster_subscription(call_id, call.ci_subscription_index + 1)
                ])

        request = subscription_request(subscriptions, self.message_id)
        await self.ws.send(json.dumps(request))
        self.message_id += 1
