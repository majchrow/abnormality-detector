import aiohttp
import asyncio
import json
import logging
import os
import signal
from aiokafka import AIOKafkaProducer
from asyncio import Queue
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial

from .client import Client
from ..config import Config


# TODO:
#  - do we even need callId at all?
#  - if Kafka producer slows down for whatever reason queues will overflow
#    - we can't drop callListUpdate events - required to know conversation state in later processing stages
#    - but we could theoretically drop roster and callInfo updates
#  - async logging


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

        if os.path.dirname(config.dumpfile):
            os.makedirs(os.path.dirname(config.dumpfile), exist_ok=True)

    def start(self):
        loop = asyncio.get_event_loop()

        signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT, signal.SIGQUIT)
        for s in signals:
            loop.add_signal_handler(s, lambda s=s: asyncio.create_task(self.shutdown(loop, signal=s)))

        def async_partial(coro_fun, *args, **kwargs):
            def run():
                return coro_fun(*args, **kwargs)
            return run

        file_flush_task = async_partial(self.flush_to_file, self.dump_queue, self.config.dumpfile)
        kafka_publish_task = async_partial(self.push_to_kafka)
        client_tasks = [async_partial(self.run_client, host, port) for host, port in self.config.addresses]

        try:
            loop.create_task(self.retry_on_failure(file_flush_task, 'flush to file task'))
            loop.create_task(self.retry_on_failure(kafka_publish_task, 'Kafka publish task'))

            for task, addr in zip(client_tasks, self.config.addresses):
                loop.create_task(self.retry_on_failure(task, f'bridge client task for {addr[0]}:{addr[1]}'))
            loop.run_forever()
        finally:
            loop.close()
            logging.info(f'{self.TAG}: shutdown complete.')

    async def retry_on_failure(self, task, name):
        backoff_s = 1

        while True:
            try:
                await task()
                return
            except asyncio.CancelledError:
                raise
            except:
                logging.exception(f'{self.TAG}: {name} failed!')
                await asyncio.sleep(backoff_s)

                # Reset so that backoff doesn't stay large all the time
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

    async def run_client(self, host: str, port: int):
        client = Client(host, port, self.config.ssl, self)
        logging.info(f'{self.TAG}: starting client for {host}:{port}...')
        await client.run(self.config.login, self.config.password, self.session)

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
        await self.dump_queue.put(json.dumps(msg, indent=4))

    async def flush_to_file(self, queue, file):
        loop = asyncio.get_running_loop()

        try:
            with ThreadPoolExecutor() as executor:
                while True:
                    msg_serialized = await queue.get()
                    task = partial(self._save_to_file, msg_serialized, file)
                    await loop.run_in_executor(executor, task)
        except asyncio.CancelledError:
            raise  # TODO: release thread locks?

    @staticmethod
    def _save_to_file(msg_serialized, filepath):
        with open(filepath, 'a') as file:
            file.write(msg_serialized + ',\n')

    ################################
    # Callbacks for Client instances
    ################################

    async def on_call_list_update(self, msg: dict, client_endpoint: Client):
        updates = msg["message"]["updates"]
        current_ts = msg["date"]  # datetime.now().isoformat()
        call = None

        for update in updates:
            update_type = update["updateType"]
            call_name = update["name"]
            call_id = update["call"]
            finished = False

            if update_type == 'add':
                if not (call := self.calls.get(call_id, None)):
                    call = self.calls[call_id] = Call(manager=self, call_name=call_name, call_id=call_id, start_datetime=current_ts)
                await call.add(client_endpoint)
            elif update_type == 'remove':
                if call_id not in self.calls:
                    logging.warning(f'{self.TAG}: received {msg} for non-tracked {call_name} {call_id}')
                    continue

                call = self.calls[call_id]
                await call.remove(client_endpoint)
                if call.done:
                    del self.calls[call_id]
                    finished = True
            else:
                call = self.calls[call_id]
            update['finished'] = finished

        if call:
            msg['startDatetime'] = call.start_datetime
            # msg['date'] = current_ts
            await self.publish(msg)
            await self.dump(msg)

    async def on_call_info_update(self, msg: dict, call_id: str):
        if not (call := self.calls.get(call_id, None)):
            logging.warning(f'{self.TAG}: received {msg} for non-tracked {call_name}')
            return

        self.timestamp(msg, call)
        await self.publish(msg)
        await self.dump(msg)

    async def on_roster_update(self, msg: dict, call_id: str):
        if not (call := self.calls.get(call_id, None)):
            logging.warning(f'{self.TAG}: received {msg} for non-tracked {call_name}')
            return
        
        self.timestamp(msg, call)
        await self.publish(msg)
        await self.dump(msg)

    @staticmethod
    def timestamp(msg, call):
        msg['startDatetime'] = call.start_datetime
        # msg['date'] = datetime.now().isoformat()
        

class Call:
    def __init__(self, manager, call_name, call_id, start_datetime):
        self.manager = manager
        self.call_name = call_name
        self.call_id = call_id
        self.handler = None
        self.clients = set()
        self.start_datetime = start_datetime 

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
            logging.info(f'{self.manager.TAG}: {self.call_name} running on {len(self.clients) + 1} servers')
        else:
            # No one's been listening so this client will
            self.handler = client
            await client.on_connect_to(self.call_name, self.call_id)
            logging.info(f'{self.manager.TAG}: {self.call_name} running on 1 server')

    async def remove(self, client):
        if client == self.handler:
            # All clients left server we've been listening to so far,
            # we need a new client to take over
            try:
                await self.handler.on_disconnect_from(self.call_name, self.call_id)
                self.handler = next(iter(self.clients))
                self.clients.discard(self.handler)
                logging.info(f'{self.manager.TAG}: handler swap for {self.call_name}')
                await self.handler.on_connect_to(self.call_name, self.call_id)
            except StopIteration:
                # No other clients
                self.handler = None
        else:
            logging.info(f'{self.manager.TAG}: secondary client disconnected for {self.call_name}')
            self.clients.remove(client)

        if self.handler:
            msg = f'{self.manager.TAG}: {self.call_name} running on {len(self.clients) + 1} server'
            if self.clients:
                msg += 's'
            logging.info(msg)
        else:
            logging.info(f'{self.manager.TAG}: {self.call_name} finished on all servers')
