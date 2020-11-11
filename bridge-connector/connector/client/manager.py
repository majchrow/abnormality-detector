import aiohttp
import asyncio
import json
import logging
import signal
from aiokafka import AIOKafkaProducer
from asyncio import Queue
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from .client import Client
from ..config import Config


# TODO:
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
    backoff_factor = 1.5
    max_backoff_s = 10

    def __init__(self, config: Config):
        self.config = config
        self.session = aiohttp.ClientSession()

        self.calls = {}
        self.dump_queue = Queue()
        self.publish_queue = Queue()

    def start(self):
        loop = asyncio.get_event_loop()

        signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT, signal.SIGQUIT)
        for s in signals:
            loop.add_signal_handler(s, lambda s=s: asyncio.create_task(self.shutdown(loop, signal=s)))
        
        try:
            loop.create_task(self.flush_to_file(self.dump_queue, self.config.dumpfile))
            loop.create_task(self.push_to_kafka())

            # TODO: drop file altogether?
            if self.config.kafka_file:
                loop.create_task(self.flush_to_file(self.publish_queue, self.config.kafka_file))
            else:
                logging.info(f'{self.TAG}: running without Kafka file dump')

            for host, port in self.config.addresses:
                loop.create_task(self.run_client(host, port))
            loop.run_forever()
        finally:
            loop.close()
            logging.info(f'{self.TAG}: shutdown complete.')

    async def run_client(self, host: str, port: int):
        client = Client(host, port, self.config.ssl, self)
        backoff_s = 1

        while True:
            try:
                logging.info(f'{self.TAG}: starting client for {host}:{port}...')
                await client.run(self.config.login, self.config.password, self.session)
            except asyncio.CancelledError:
                raise
            except:
                logging.exception(f'{self.TAG}: run failed!')
                await asyncio.sleep(backoff_s)

                # Reset so that doesn't stay large all the time
                if (backoff_s := backoff_s * self.backoff_factor) > self.max_backoff_s:
                    backoff_s = 1

    async def shutdown(self, loop, signal):
        if signal:
            logging.info(f'{self.TAG}: received exit signal {signal.name}...')

        await self.session.close()
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [task.cancel() for task in tasks]

        logging.info(f"{self.TAG}: cancelling {len(tasks)} outstanding tasks")
        await asyncio.gather(*tasks, return_exceptions=True)
        
        loop.stop()

    async def publish(self, msg: dict):
        await self.publish_queue.put(msg)

    async def push_to_kafka(self):
        if not self.config.kafka_bootstrap_address:
            logging.info(f'{self.TAG}: running without Kafka publisher')
            return

        producer = AIOKafkaProducer(bootstrap_servers=self.config.kafka_bootstrap_address)
        await producer.start()

        logging.info(f'{self.TAG}: Kafka publisher started')
        try:
            while True:
                msg_dict = await self.publish_queue.get()
                payload = json.dumps(msg_dict).encode()
                topic = msg_dict['message']['type']
                await producer.send_and_wait(topic, payload)
        finally:
            logging.info(f'{self.TAG}: Kafka publisher stopped')
            await producer.stop()

    async def dump(self, msg: dict):
        await self.dump_queue.put(msg)

    async def flush_to_file(self, queue, file):
        loop = asyncio.get_running_loop()

        try:
            with ThreadPoolExecutor() as executor:
                while True:
                    msg_dict = await queue.get()
                    task = partial(self._save_to_file, msg_dict, file)
                    await loop.run_in_executor(executor, task)
        except asyncio.CancelledError:
            raise  # TODO: release thread locks?

    @staticmethod
    def _save_to_file(msg_dict, filepath):
        with open(filepath, 'a') as file:
            json.dump(msg_dict, file, indent=4)
            file.write(",\n")

    async def on_add_call(self, call_name: str, call_id: str, client_endpoint: Client):
        if call_id not in self.calls:
            self.calls[call_id] = Call(manager=self, call_name=call_name, call_id=call_id)
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
    def __init__(self, manager, call_name, call_id):
        self.manager = manager
        self.call_name = call_name
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
            await client.on_connect_to(self.call_name, self.call_id)

    async def remove(self, client):
        if client == self.handler:
            # All clients left server we've been listening to so far,
            # we need a new client to take over
            try:
                self.handler = next(iter(self.clients))
                self.clients.discard(self.handler)
                await self.handler.on_connect_to(self.call_name, self.call_id)
            except StopIteration:
                # No other clients
                self.handler = None
        else:
            self.clients.remove(client)
