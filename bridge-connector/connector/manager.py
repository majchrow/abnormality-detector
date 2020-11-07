import asyncio
import logging
from asyncio import Queue

from config import Config
from connector.client import Client, TokenManager


# TODO:
#  - shutdown (cancel Client coroutines)
#  - exception handling
#    - failure to fetch token
#    -
#  - async logging and saving to file
#  - publishing to Kafka


# IDEA:
#  ClientManager organizes Clients responsible for communication with Meeting Servers.
#  He keeps track of all ongoing conferences (`ClientManager#calls`). For each conference
#  he knows which Meeting Servers host it (`Call#clients`) and which Client is listening
#  to events from this conversation (if any) (`Call#handler`).
#
# Each Client is responsible for transparent communication with exactly one Meeting Server.
# Clients forward all 'add', 'update' and 'remove' events to ClientManager so that he's up
# to date on currently ongoing conversations. He then makes sure that at most one Client is
# listening to given conversation. If e.g. all participants from given server leave the
# conversation, it prompts another Client to start listening, if he can find any Client with
# free WebSocket connections available.
class ClientManager:

    TAG = 'ClientManager'

    def __init__(self, config: Config):
        self.config = config
        self.calls = {}
        self.log_queue = Queue()

    def start(self):
        loop = asyncio.get_event_loop()

        try:
            loop.create_task(self.save_log())
            for host, port in self.config.addresses:
                loop.create_task(self.run_client(host, port))
            loop.run_forever()
        finally:
            loop.close()
            logging.info(f'{self.TAG}: shutdown complete.')

    async def run_client(self, host: str, port: int):
        async with TokenManager(host, port, self.config.login, self.config.password) as token_manager:
            client = Client(host, port, self, token_manager, self.config.max_ws_connections)
            await client.run()

    async def log(self, msg: dict):
        await self.log_queue.put(msg)

    async def save_log(self):
        while True:
            msg = await self.log_queue.get()
            print(msg)  # TODO

    async def on_add_call(self, call_id: str, client_endpoint: Client):
        if call_id not in self.calls:
            self.calls[call_id] = Call(manager=self, call_id=call_id)
        await self.calls[call_id].add(client_endpoint)

    async def on_update_call(self, call_id: str, client_endpoint: Client):
        pass  # TODO: don't know yet, maybe when call becomes distributed??

    async def on_remove_call(self, call_id: str, client_endpoint: Client):
        if call_id not in self.calls:
            return

        call = self.calls[call_id]
        await call.remove(client_endpoint)
        if call.done:
            del self.calls[call_id]

    async def on_resource_released(self, client_endpoint: Client):
        for call in self.calls.values():
            if not call.handled and client_endpoint in call.clients:
                call.add(client_endpoint)
            break


class Call:
    def __init__(self, manager, call_id):
        self.manager = manager
        self.call_id = call_id
        self.handler = None
        self.clients = set()

    @property
    def handled(self):
        return self.handler is not None

    @property
    def done(self):
        return len(self.clients) == 0 and self.handler is None

    async def add(self, client):
        if self.handled:
            # Some client is listening already
            self.clients.add(client)
        elif client.available:
            # No one's been listening but this client can
            self.clients.discard(client)
            self.handler = client
            await client.on_connect_to(self.call_id)
        else:
            # No one has free WebSockets to start listening now
            self.clients.add(client)

    async def remove(self, client):
        if client == self.handler:
            # All clients left server we've been listening to so far,
            # we need a new client to take over if we can find any
            for c in self.clients:
                if c.available:
                    self.handler = c
                    await self.handler.on_connect_to(self.call_id)
                    break
            else:
                self.handler = None

            # This client now has one more free WebSocket - it should
            # start handling some new conference if we can find one
            await self.manager.on_resource_released(client)
        else:
            self.clients.remove(client)
