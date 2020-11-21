import asyncio
import json
import logging
from aiohttp import web
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from asyncio import Queue
from contextlib import contextmanager
from typing import List, Optional

from ..config import Config
from ..db import CassandraDAO
from ..exceptions import MonitoringNotSupportedError, UnmonitoredError
from .thresholds import validate, STREAM_FINISHED


# TODO:
#  important: after consumer group re-balance still every (!) worker process receives
#  data messages and
class Manager:

    TAG = 'Manager'

    def __init__(self, dao: CassandraDAO, config: Config):
        self.dao: CassandraDAO = dao
        self.kafka_manager = KafkaManager(config.kafka_bootstrap_server, config.kafka_call_list_topic)
        self.num_workers = config.num_workers
        self.workers = []

        # TODO: other managers for e.g. running ML predictions, retraining model etc.

    def start(self):
        asyncio.create_task(self.kafka_manager.run())
        asyncio.create_task(self._bootstrap())

    async def _bootstrap(self):
        for i in range(self.num_workers):
            worker = ChildProcess(f'worker-{i}')
            worker.start()
            self.workers.append(worker)

        # TODO: retry on failure
        monitored = await self.dao.get_monitored_meetings()
        for meeting in monitored:
            criteria = json.loads(meeting['criteria'])
            await self.kafka_manager.publish(
                'monitoring-config',
                meeting['name'],
                json.dumps({'config_type': 'update', 'criteria': [c.dict() for c in criteria]})
            )
        logging.info(f'{self.TAG}: bootstrapped from {len(monitored)} meetings')

    async def schedule(self, conf_name: str, criteria: List[dict], monitoring_type: str):
        if monitoring_type == 'threshold':
            criteria = validate(criteria)

            await self.dao.set_monitoring_status(conf_name, monitored=True)
            await self.kafka_manager.publish(
                'monitoring-config',
                conf_name,
                json.dumps({'config_type': 'update', 'criteria': [c.dict() for c in criteria]})
            )
            logging.info(f'{self.TAG}: scheduled monitoring for {conf_name}')
        else:
            raise MonitoringNotSupportedError()

    async def unschedule(self, conf_name: str, monitoring_type: str):
        if monitoring_type == 'threshold':
            await self.dao.set_monitoring_status(conf_name, monitored=False)
            await self.kafka_manager.publish(
                'monitoring-config', conf_name, json.dumps({'config_type': 'delete'})
            )
            logging.info(f'{self.TAG}: unscheduled monitoring for {conf_name}')
        else:
            raise MonitoringNotSupportedError()

    async def get_all_monitored(self):
        # TODO: test if DAO works
        monitored = await self.dao.get_monitored_meetings()
        return [meeting['name'] for meeting in monitored]

    async def is_monitored(self, conf_name: str):
        # TODO: test if it returns a boolean
        return await self.dao.is_monitored(conf_name)

    @contextmanager
    def calls_receiver(self):
        queue = Queue()

        async def _listen():
            self.kafka_manager.call_event_subscribe(queue)
            while True:
                msg = await queue.get()
                yield msg

        try:
            yield _listen
        finally:
            self.kafka_manager.call_event_unsubscribe(queue)

    async def monitoring_receiver(self, call_name, monitoring_type: str):
        if not (await self.is_monitored(call_name)):
            raise UnmonitoredError()
        if monitoring_type != 'threshold':
            raise MonitoringNotSupportedError()

        @contextmanager
        def _listen_manager():
            queue = Queue()

            async def _listen():
                self.kafka_manager.monitoring_subscribe(call_name, queue)
                while True:

                    msg = await queue.get()
                    if msg == STREAM_FINISHED:
                        break
                    yield msg

            try:
                yield _listen
            finally:
                self.kafka_manager.monitoring_unsubscribe(call_name, queue)

        return _listen_manager

    async def shutdown(self):
        logging.info(f'{self.TAG}: shutdown finished')


class ChildProcess:
    def __init__(self, uid: str):
        self.uid = uid
        self.worker = None
        self.task = None

    def start(self):
        self.task = asyncio.create_task(self._run())

    async def stop(self):
        self.task.cancel()
        await self.task

    async def _run(self):
        self.worker = await asyncio.create_subprocess_exec(
            'python3', '-m', 'streaming.monitoring.thresholds.monitor', self.uid,
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        asyncio.create_task(self._listen(self.worker.stdout))
        asyncio.create_task(self._listen(self.worker.stderr))
        # TODO: some life check and restart! (worker.is_alive()?)

    async def _listen(self, stream):
        while True:
            line = (await stream.readline()).decode()
            if not line:
                await asyncio.sleep(1)
            else:
                logging.info(f'{self.uid}: {line}')


class KafkaManager:

    TAG = 'KafkaManager'

    def __init__(self, bootstrap_server, call_list_topic):
        self.bootstrap_server = bootstrap_server
        self.call_list_topic = call_list_topic
        self.call_event_listeners = set()
        self.anomaly_listeners = {}

        self.consumer = None
        self.producer = None

    async def run(self):
        self.consumer = AIOKafkaConsumer(
            self.call_list_topic, 'monitoring-anomalies', bootstrap_servers='kafka:29092',
        )
        await self.consumer.start()

        self.producer = AIOKafkaProducer(bootstrap_servers='kafka:29092')
        await self.producer.start()

        try:
            async for msg in self.consumer:
                msg_dict = json.loads(msg.value.decode())

                if msg.topic == self.call_list_topic:
                    call_name = msg_dict['name']
                    if msg_dict['finished']:
                        event = 'Meeting finished'
                    elif msg_dict['start_datetime'] == msg_dict['last_update']:
                        event = 'Meeting started'
                    else:
                        event = None
                    if event and self.call_event_listeners:
                        msg = {'name': call_name, 'event': event}
                        logging.info(f'pushing call info {msg} to {len(self.call_event_listeners)} subscribers')
                        for queue in self.call_event_listeners:
                            queue.put_nowait(msg)
                    continue

                if not (listeners := self.anomaly_listeners.get(msg_dict['meeting'], None)):
                    continue

                logging.info(f'{self.TAG}: pushing {msg_dict} to {len(listeners)} listeners')
                for queue in listeners:
                    queue.put_nowait(msg_dict['anomalies'])
        finally:
            await self.consumer.stop()
            await self.producer.stop()

    async def publish(self, topic: str, key: Optional[str], value: str):
        key = key.encode() if key else key
        await self.producer.send_and_wait(topic=topic, key=key, value=value.encode())

    def call_event_subscribe(self, queue):
        logging.info(f'{self.TAG}: registered call event subscriber')
        self.call_event_listeners.add(queue)

    def call_event_unsubscribe(self, queue):
        if queue in self.call_event_listeners:
            self.call_event_listeners.remove(queue)
            logging.info(f'{self.TAG}: unregistered call event subscriber')
        else:
            logging.info(f'{self.TAG}: "unsubscribe call events" attempt - subscriber not found')

    def monitoring_subscribe(self, conf_name: str, queue):
        logging.info(f'{self.TAG}: registered subscriber for {conf_name}')

        if (sinks := self.anomaly_listeners.get(conf_name, None)) is None:
            sinks = set()
            self.anomaly_listeners[conf_name] = sinks
        sinks.add(queue)

    def monitoring_unsubscribe(self, conf_name: str, queue):
        if not (sinks := self.anomaly_listeners.get(conf_name, None)):
            logging.warning(f'{self.TAG}: "unsubscribe" attempt for {conf_name} - conference unmonitored!')
        else:
            try:
                sinks.remove(queue)
                logging.info(f'{self.TAG}: unregistered subscriber for {conf_name}')
                if not sinks:
                    del self.anomaly_listeners[conf_name]
            except KeyError:
                logging.warning(f'{self.TAG}: "unsubscribe" attempt for {conf_name} - not a subscriber!')


async def start_all(app: web.Application):
    app['monitoring'].start()


async def cancel_all(app: web.Application):
    await app['monitoring'].shutdown()


def setup_monitoring(app: web.Application, config):
    dao = app['db']
    manager = Manager(dao, config)
    app['monitoring'] = manager
    app.on_startup.append(start_all)
    app.on_cleanup.append(cancel_all)
