import asyncio
import logging
from asyncio import Queue
from typing import Tuple

from connector.client import Client, TokenManager

# TODO:
#  - shutdown (cancel Client coroutines)
#  - ...


class ClientManager:
    def __init__(self, login: str, password: str, config):
        self.login = login
        self.password = password
        self.addresses = config.addresses
        self.logfile = config.logfile
        self.max_ws_count = config.max_ws_count
        self.calls = {}
        self.log_queue = Queue()

    def start(self):
        loop = asyncio.get_event_loop()

        # TODO: do we need this try-catch clause?
        try:
            loop.create_task(self.save_log())
            for addr in self.addresses:
                loop.create_task(self.run_client(addr))
            loop.run_forever()
        finally:
            loop.close()
            logging.info('Client manager shutdown.')

    async def run_client(self, address: Tuple[str, str]):
        host, port = address
        async with TokenManager(host, port, self.login, self.password) as token_manager:
            client = Client(address, self, token_manager, self.max_ws_count)
            await client.run()

    async def log(self, msg):
        await self.log_queue.put(msg)

    async def save_log(self):
        # TODO: use enable_logger?
        while True:
            msg = await self.log_queue.get()
            print(msg)  # TODO

    async def on_add_call(self, call_id, client_endpoint):
        if call_id not in self.calls:
            self.calls[call_id] = Call(call_id=call_id)
        await self.calls[call_id].add(client_endpoint)

    async def on_update_call(self, call_id, client_endpoint):
        pass  # TODO: don't know yet, maybe when call becomes distributed??

    async def on_remove_call(self, call_id, client_endpoint):
        if call_id in self.calls:
            await self.calls[call_id].remove(client_endpoint)


class Call:
    def __init__(self, call_id):
        self.call_id = call_id
        self.handler = None
        self.clients = set()

    @property
    def active(self):
        return self.handler is not None

    async def add(self, client):
        if self.active:
            # Some client is handling it already
            self.clients.add(client)
        elif client.available:
            self.handler = client
            await client.on_connect_to(self.call_id)
        else:
            self.clients.add(client)

    async def remove(self, client):
        if client == self.handler:
            # We need a new handler if we can find any
            for c in self.clients:
                if c.available:
                    self.handler = c
                    await self.handler.on_connect_to(self.call_id)
            else:
                self.handler = None
        else:
            self.clients.remove(client)
