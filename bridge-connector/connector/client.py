import aiohttp
import asyncio
import json
import logging
from datetime import datetime

from websockets import connect

from connector.protocol import (
    ack, calls_subscription, call_info_subscription, call_roster_subscription,subscription_request
)


class Client:
    """Multi-socket client for a single bridge server."""
    def __init__(self, address, call_manager, token_manager, max_ws_count):
        self.host, self.port = address
        self.call_manager = call_manager
        self.token_manager = token_manager
        self.max_ws_count = max_ws_count
        self.main_handler = None
        self.call_handlers = {}

    @property
    def available(self):
        return len(self.call_handlers) < self.max_ws_count

    def start(self):
        asyncio.create_task(self.run_main_handler())

    async def run_main_handler(self):
        uri = f"wss://{self.host}:{self.port}/events/v1?authToken={self.token_manager.token}"
        # noinspection PyTypeChecker
        async with connect(uri, ping_timeout=None) as ws:
            self.main_handler = ConnectionHandler(ws, self)
            self.main_handler.processing_stages = [self.main_handler.dispatch_call_list_update]
            await self.main_handler.calls_subscribe()
            await self.main_handler.run()

    async def run_secondary_handler(self, call_id):
        uri = f"wss://{self.host}:{self.port}/events/v1?authToken={self.token_manager.token}"
        # noinspection PyTypeChecker
        async with connect(uri, ping_timeout=None) as ws:
            handler = ConnectionHandler(ws, self)
            handler.processing_stages = [handler.process_call_roster_update]
            self.call_handlers[call_id] = handler
            await handler.call_subscribe(call_id)
            await handler.run()

    async def on_add_call(self, call_id):
        await self.call_manager.on_add_call(call_id, self)

    async def on_update_call(self, call_id):
        await self.call_manager.on_add_call(call_id, self)

    async def on_remove_call(self, call_id):
        await self.call_manager.on_remove_call(call_id, self)

        try:
            handler = self.call_handlers[call_id]
            if handler == self.main_handler:
                await handler.calls_subscribe()
                handler.processing_stages.pop()
            else:
                await handler.stop()
                del self.call_handlers[call_id]
        except KeyError:
            pass

    async def on_call_roster_update(self, msg_dict):
        # TODO: create_task maybe, JIC of full queue
        await self.call_manager.log(msg_dict)

    async def on_connect_to(self, call_id):
        if len(self.call_handlers) == 0:
            self.call_handlers[call_id] = self.main_handler
            await self.main_handler.all_subscribe(call_id)
            self.main_handler.processing_stages.append(ConnectionHandler.process_call_roster_update)
        else:
            asyncio.create_task(self.run_secondary_handler(call_id))


class ConnectionHandler:
    def __init__(self, ws, owner):
        self.ws = ws
        self.message_id = 0  # TODO: increment it actually
        self.owner = owner
        self.processing_stages = []
        self.running = False
        self.stopped = asyncio.Event()

    async def stop(self):
        self.running = False
        await self.stopped.wait()

    async def run(self):
        self.running = True
        while self.running:
            msg = await self.ws.recv()
            msg_dict = json.loads(msg)
            msg_id = await self.process_message(msg_dict)
            if msg_id:
                await self.ws.send(json.dumps(ack(msg_id)))  # acknowledge
        self.stopped.set()

    class UnsupportedError(Exception):
        """Processing stage does not handle this message type."""
        pass

    async def process_message(self, msg_dict):
        # note: could also be "messageAck" - we ignore it
        if msg_dict["type"] != "message":
            return

        msg_type = msg_dict["message"]["type"]

        for stage in self.processing_stages:
            try:
                await stage(msg_dict, msg_type)
                break
            except ConnectionHandler.UnsupportedError:
                pass
        return msg_dict["message"]["messageId"]

    # Init stages
    async def calls_subscribe(self):
        request = subscription_request([calls_subscription], self.message_id)
        await self.ws.send(json.dumps(request))

    async def call_subscribe(self, call_id):
        subscriptions = [call_info_subscription(call_id), call_roster_subscription(call_id)]
        request = subscription_request(subscriptions, self.message_id)
        await self.ws.send(json.dumps(request))

    # Processing stages
    async def dispatch_call_list_update(self, msg_dict, msg_type):
        if "callListUpdate" not in msg_type:
            raise ConnectionHandler.UnsupportedError

        updates = msg_dict["message"]["updates"]
        for update in updates:
            call_id = update["call"]
            update_type = update["updateType"]
            await self.dispatch(call_id, update_type)

    async def dispatch(self, call_id, update_type):
        method_name = f'on_{update_type}_call'
        try:
            method = getattr(self.owner, method_name)
            await method(call_id, self)
        except AttributeError:
            pass  # TODO: log error

    async def process_call_roster_update(self, msg_dict,  msg_type):
        if not ("callInfoUpdate" in msg_type or "rosterUpdate" in msg_type):
            raise ConnectionHandler.UnsupportedError

        await self.owner.on_call_roster_update(msg_dict)


###
# We ain't go no further
###
class TokenManager:
    """Encapsulates token API access to prevent redundant refreshes."""
    def __init__(self, host, port, login, password):
        self.url = f'https://{host}:{port}/api/v1/authTokens'
        self.auth = aiohttp.BasicAuth(login, password)

        self.auth_token = None
        self.refresh_interval_s = 10
        self.is_fresh = False
        self.refresh_lock = asyncio.Lock()
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()

    async def __aexit__(self, *args):
        await self.session.close()

    async def token(self):
        if not self.auth_token:
            await self.refresh()
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
