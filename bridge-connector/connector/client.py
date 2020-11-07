import aiohttp
import asyncio
import json
import logging

from websockets import connect

from connector.protocol import (
    ack, calls_subscription, call_info_subscription, call_roster_subscription,subscription_request
)


class Client:

    TAG = 'Client'

    """Multi-socket client for a single bridge server."""
    def __init__(self, host: str, port: int, call_manager, token_manager, max_ws_count: int):
        self.host = host
        self.port = port
        self.call_manager = call_manager
        self.token_manager = token_manager
        self.max_ws_count = max_ws_count
        self.main_handler = None
        self.call_handlers = {}

    @property
    def available(self):
        return len(self.call_handlers) < self.max_ws_count

    @property
    def event_uri(self):
        return f"wss://{self.host}:{self.port}/events/v1?authToken={self.token_manager.token}"

    async def run(self):
        # noinspection PyTypeChecker
        async with connect(self.event_uri, ping_timeout=None) as ws:
            self.main_handler = ConnectionHandler(ws, self)
            await self.main_handler.calls_subscribe()
            await self.main_handler.run()

    async def run_secondary_handler(self, call_id):
        # noinspection PyTypeChecker
        async with connect(self.event_uri, ping_timeout=None) as ws:
            handler = ConnectionHandler(ws, self)
            self.call_handlers[call_id] = handler
            await handler.call_subscribe(call_id)
            await handler.run()

    async def on_calls_update(self, call_id, update_type):
        if update_type == 'add':
            await self.call_manager.on_add_call(call_id, self)
        elif update_type == 'update':
            await self.call_manager.on_update_call(call_id, self)
        elif update_type == 'remove':
            try:
                handler = self.call_handlers[call_id]
                if handler == self.main_handler:
                    await handler.calls_subscribe()
                else:
                    await handler.stop()
                    del self.call_handlers[call_id]
            except KeyError:
                pass
            await self.call_manager.on_remove_call(call_id, self)
        else:
            logging.error(f'{self.TAG}: received calls update of type {update_type}')

    async def on_call_roster_update(self, msg_dict):
        await self.call_manager.log(msg_dict)

    async def on_connect_to(self, call_id):
        if len(self.call_handlers) == 0:
            self.call_handlers[call_id] = self.main_handler
            await self.main_handler.full_subscribe(call_id)
        else:
            asyncio.create_task(self.run_secondary_handler(call_id))


class ConnectionHandler:

    TAG = 'ConnectionHandler'

    def __init__(self, ws, owner):
        self.ws = ws
        self.owner = owner
        self.message_id = 0
        self.running = False
        self.stopped = asyncio.Event()

    async def run(self):
        self.running = True
        while self.running:
            msg = await self.ws.recv()
            msg_dict = json.loads(msg)
            msg_id = await self.process_message(msg_dict)
            if msg_id:
                await self.ws.send(json.dumps(ack(msg_id)))  # acknowledge
        self.stopped.set()

    async def stop(self):
        self.running = False
        await self.stopped.wait()

    async def calls_subscribe(self):
        await self._subscribe([calls_subscription])

    async def call_subscribe(self, call_id):
        subscriptions = [call_info_subscription(call_id), call_roster_subscription(call_id)]
        await self._subscribe(subscriptions)

    async def full_subscribe(self, call_id):
        subscriptions = [calls_subscription, call_info_subscription(call_id), call_roster_subscription(call_id)]
        await self._subscribe(subscriptions)

    async def _subscribe(self, subscriptions):
        request = subscription_request(subscriptions, self.message_id)
        await self.ws.send(json.dumps(request))
        self.message_id += 1

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
                await self.owner.on_calls_update(call_id, update_type)
        elif "callInfoUpdate" in msg_type or "rosterUpdate" in msg_type:
            await self.owner.on_call_roster_update(msg_dict)
        else:
            logging.error(f'{self.TAG}: unknown message type {msg_type}')


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
