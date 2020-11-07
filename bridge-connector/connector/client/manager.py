import aiohttp
import asyncio
import json
import logging
import signal
from asyncio import Queue
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial

from .client import Client
from ..config import Config


# TODO:
#  - add call ID info to messages saved to file/pushed to Kafka
#    - WHAT FORMAT?
#  - exception handling
#    - failure to fetch token
#    - HTTP 401 (?) error - refresh token?
#  - async logging and saving to file
#  - publishing to Kafka


# IDEA:
#  ClientManager organizes Clients responsible for communication with Meeting Servers.
#  He keeps track of all ongoing conferences (`ClientManager#calls`). For each conference
#  he knows which Meeting Servers host it (`Call#clients`) and which Client is listening
#  to events from this conversation (`Call#handler`).
#
# Each Client is responsible for transparent communication with exactly one Meeting Server.
# Clients forward all 'add', 'update' and 'remove' events to ClientManager so that he's up
# to date on currently ongoing conversations. He then makes sure that at most one Client is
# listening to given conversation. If e.g. all participants from given server leave the
# conversation, it prompts another Client to start listening.
class ClientManager:

    TAG = 'ClientManager'

    def __init__(self, config: Config):
        self.config = config
        self.session = aiohttp.ClientSession()

        self.calls = {}
        self.log_queue = Queue()

    def start(self):
        loop = asyncio.get_event_loop()

        signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT, signal.SIGQUIT)
        for s in signals:
            loop.add_signal_handler(s, lambda s=s: asyncio.create_task(self.shutdown(loop, signal=s)))
        
        try:
            loop.create_task(self.save_log())
            for host, port in self.config.addresses:
                loop.create_task(self.run_client(host, port))
            loop.run_forever()
        finally:
            loop.close()
            logging.info(f'{self.TAG}: shutdown complete.')

    async def run_client(self, host: str, port: int):
        client = Client(host, port, self)
        while True:
            try:
                logging.info(f'{self.TAG}: starting client for {host}:{port}...')
                await client.run(self.config.login, self.config.password, self.session)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logging.error(f'{self.TAG}: client run failed with {e}')

    async def shutdown(self, loop, signal):
        if signal:
            logging.info(f'{self.TAG}: received exit signal {signal.name}...')

        await self.session.close()
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [task.cancel() for task in tasks]

        logging.info(f"{self.TAG}: cancelling {len(tasks)} outstanding tasks")
        await asyncio.gather(*tasks, return_exceptions=True)

        loop.stop()

    async def log(self, msg: dict, call_id: str):
        await self.log_queue.put((msg, call_id))

    async def save_log(self):
        loop = asyncio.get_running_loop()

        try:
            with ThreadPoolExecutor() as executor:
                while True:
                    msg, call_id = await self.log_queue.get()
                    msg_dict['date'] = datetime.now().isoformat()
                    msg_dict['call'] = call_id
                    task = partial(self._save_to_file, msg)
                    await loop.run_in_executor(executor, task)
        except asyncio.CancelledError:
            pass  # TODO: release thread locks?

    def _save_to_file(self, msg_dict):
        with open(self.config.logfile, "a") as file:
            json.dump(msg_dict, file, indent=4)
            file.write(",\n")

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
        else:
            # No one's been listening so this client will
            # self.clients.discard(client)
            self.handler = client
            await client.on_connect_to(self.call_id)

    async def remove(self, client):
        if client == self.handler:
            # All clients left server we've been listening to so far,
            # we need a new client to take over
            try:
                self.handler = next(iter(self.clients))
                self.clients.discard(self.handler)
                await self.handler.on_connect_to(self.call_id)
            except StopIteration:
                # No other clients
                self.handler = None
        else:
            self.clients.remove(client)
