import aiohttp
import asyncio
import json
import logging

from websockets import connect

from .protocol import (
    ack, calls_subscription, call_info_subscription, call_roster_subscription,subscription_request
)


class Client:

    TAG = 'Client'

    """Multi-socket client for a single bridge server."""
    def __init__(self, host: str, port: int, call_manager, token_manager):
        self.host = host
        self.port = port
        self.TAG += f' {host}:{port}'
        self.call_manager = call_manager
        self.token_manager = token_manager

        self.ws = None
        self.message_id = 0
        self.subscription_ind = 2
        self.call_ids = {}  # subscription index -> call ID
        self.subscriptions = {}  # call ID -> call info subscription index

    @property
    def event_uri(self):
        return f"wss://{self.host}:{self.port}/events/v1?authToken={self.token_manager.token}"

    async def run(self):
        # noinspection PyTypeChecker
        async with connect(self.event_uri, ping_timeout=None) as ws:
            self.ws = ws
            await self._subscribe()

            while True:
                msg = await ws.recv()
                msg_dict = json.loads(msg)
                msg_id = await self.process_message(msg_dict)
                if msg_id:
                    await ws.send(json.dumps(ack(msg_id)))  # acknowledge

    async def process_message(self, msg_dict):
        logging.info(f'{self.TAG}: RECEIVED: {msg_dict}')

        # note: could also be "messageAck" - we ignore it
        if msg_dict["type"] != "message":
            return

        msg_type = msg_dict["message"]["type"]
        if "callListUpdate" in msg_type:
            updates = msg_dict["message"]["updates"]
            for update in updates:
                call_id = update["call"]
                update_type = update["updateType"]
                await self.on_calls_update(call_id, update_type)
        elif "callInfoUpdate" in msg_type or "rosterUpdate" in msg_type:
            index = msg_dict["message"]["subscriptionIndex"]
            if index in self.call_ids:
                call_id = self.call_ids[index]
                await self.call_manager.log(msg_dict, call_id)
            else:
                logging.warning(f'{self.TAG}: received update after "remove": {msg_dict}')
        elif "subscriptionUpdate" in msg_type:
            pass
        else:
            logging.error(f'{self.TAG}: unknown message type {msg_type}')
            return

        return msg_dict["message"]["messageId"]

    async def on_connect_to(self, call_id):
        self._add_call(call_id)
        await self._subscribe()

    def _add_call(self, call_id):
        # Setup subscription indexes for call info and roster info
        s_ind = self.subscription_ind
        self.subscription_ind += 2

        self.subscriptions[call_id] = s_ind
        self.call_ids[s_ind] = self.call_ids[s_ind + 1] = call_id

    async def _subscribe(self):
        subscriptions = [calls_subscription]

        for call_id in self.subscriptions:
            call_info_sub_ind = self.subscriptions[call_id]

            subscriptions.extend([
                call_info_subscription(call_id, call_info_sub_ind),
                call_roster_subscription(call_id, call_info_sub_ind + 1)
            ])

        request = subscription_request(subscriptions, self.message_id)
        await self.ws.send(json.dumps(request))
        self.message_id += 1

    async def on_calls_update(self, call_id, update_type):
        if update_type == 'add':
            await self.call_manager.on_add_call(call_id, self)
        elif update_type == 'update':
            await self.call_manager.on_update_call(call_id, self)
        elif update_type == 'remove':
            if call_id in self.subscriptions:
                # TODO: should we subscribe again immediately?
                s_ind = self.subscriptions[call_id]
                del self.call_ids[s_ind]
                del self.call_ids[s_ind + 1]
                del self.subscriptions[call_id]
            await self.call_manager.on_remove_call(call_id, self)
        else:
            logging.error(f'{self.TAG}: received calls update of type {update_type}')


class TokenManager:
    """Encapsulates token API access to prevent redundant refreshes."""
    def __init__(self, host: str, port: int, login: str, password: str):
        self.url = f'https://{host}:{port}/api/v1/authTokens'
        self.auth = aiohttp.BasicAuth(login, password)
        self.session = None

        self.auth_token = None
        self.is_fresh = False
        self.refresh_lock = asyncio.Lock()
        self.refresh_interval_s = 10

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        await self.refresh()
        return self

    async def __aexit__(self, *args):
        await self.session.close()

    @property
    def token(self):
        return self.auth_token

    async def refresh(self):
        async with self.refresh_lock:
            if self.is_fresh:
                return

        async with self.session.post(self.url, data={}, auth=self.auth) as response:
            self.auth_token = response.headers["X-Cisco-CMS-Auth-Token"]
            self.is_fresh = True
        asyncio.create_task(self._expire())

    async def _expire(self):
        await asyncio.sleep(self.refresh_interval_s)
        async with self.refresh_lock:
            self.is_fresh = False
