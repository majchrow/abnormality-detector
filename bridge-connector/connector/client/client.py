import aiohttp
import json
import logging
from datetime import datetime
from collections import namedtuple
from aiohttp import ClientConnectionError
from websockets import connect

from .protocol import (
    ack, calls_subscription, call_info_subscription, call_roster_subscription,subscription_request
)


class Client:

    TAG = 'Client'

    Call = namedtuple('Call', ['name', 'id', 'ci_subscription_index'])

    def __init__(self, host: str, port: int, call_manager):
        self.host = host
        self.port = port
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
        self.call_ids = {}              # call ID -> Call

    @property
    def token_uri(self):
        return f'https://{self.host}:{self.port}/api/v1/authTokens'

    @property
    def event_uri(self):
        return f"wss://{self.host}:{self.port}/events/v1?authToken={self.auth_token}"

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
            updates = msg_dict["message"]["updates"]
            for update in updates:
                await self.on_calls_update(update)
                await self.call_manager.dump(msg_dict)
                await self.publish(msg_dict, msg_type)
        elif msg_type == "callInfoUpdate" or msg_type == "rosterUpdate":
            index = msg_dict["message"]["subscriptionIndex"]
            if index in self.subscriptions:
                await self.call_manager.dump(msg_dict)
                await self.publish(msg_dict, msg_type)
            else:
                logging.warning(f'{self.TAG}: received update after "remove": {msg_dict}')
        elif "subscriptionUpdate" in msg_type:
            await self.call_manager.dump(msg_dict)
        else:
            logging.warning(f'{self.TAG}: unknown message type {msg_type}')
            return

        return msg_dict["message"]["messageId"]

    # What's missing:
    #  - callListUpdate - only "add" has both name and callId, others only have callId
    #  - callInfoUpdate - only name
    #  - rosterUpdate - neither
    async def publish(self, msg_dict: dict, msg_type: str):
        # Add timestamp and missing info (call ID and call name) to the message
        msg_dict['date'] = datetime.now().isoformat()

        if msg_type == "callListUpdate":
            updates = msg_dict["message"]["updates"]
            if not updates:
                logging.warning(f'{self.TAG}: "callListUpdate" message with empty "updates" list')
                return

            call_id = updates[0]["call"]
            if call_id not in self.call_ids:
                # Conference this client does not handle
                return

            call = self.call_ids[call_id]
            for update in updates:
                update['name'] = call.name
        else:
            index = msg_dict["message"]["subscriptionIndex"]
            call = self.subscriptions[index]
            if msg_type == 'callInfoUpdate':
                msg_dict["message"]["callInfo"]["call"] = call.id
            else:
                msg_dict["call"] = call.id
                msg_dict["name"] = call.name

        await self.call_manager.publish(msg_dict)

    async def on_calls_update(self, update):
        update_type = update["updateType"]
        call_id = update["call"]

        if update_type == 'add':
            call_name = update["name"]
            await self.call_manager.on_add_call(call_name, call_id, self)
        elif update_type == 'update':
            await self.call_manager.on_update_call(call_id, self)
        elif update_type == 'remove':
            if call_id in self.call_ids:
                call = self.call_ids[call_id]
                s_ind = call.ci_subscription_index

                del self.subscriptions[s_ind]
                del self.subscriptions[s_ind + 1]
                del self.call_ids[call_id]

                # TODO: should we subscribe again immediately?
                await self.call_manager.on_remove_call(call_id, self)
                logging.info(f'{self.TAG}: removed call {call.name} with ID {call_id}')
        else:
            logging.warning(f'{self.TAG}: received calls update of type {update_type}')

    async def on_connect_to(self, call_name, call_id):
        # Setup subscription indexes for call info and roster info
        s_ind = self.subscription_ind
        self.subscription_ind += 2

        call = Client.Call(name=call_name, id=call_id, ci_subscription_index=s_ind)
        self.subscriptions[s_ind] = self.subscriptions[s_ind + 1] = call
        self.call_ids[call_id] = call

        # Send server subscription
        await self._subscribe()
        logging.info(f'{self.TAG}: subscribed to call {call_name} with ID {call_id}')

    async def _subscribe(self):
        subscriptions = [calls_subscription]

        for call_id, call in self.call_ids.items():
            subscriptions.extend([
                call_info_subscription(call_id, call.ci_subscription_index),
                call_roster_subscription(call_id, call.ci_subscription_index + 1)
            ])

        request = subscription_request(subscriptions, self.message_id)
        await self.ws.send(json.dumps(request))
        self.message_id += 1

