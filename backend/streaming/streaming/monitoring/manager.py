import asyncio
import json
import logging
from aiohttp import web
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from asyncio import Queue
from contextlib import contextmanager
from typing import List

from ..config import Config
from ..exceptions import MonitoringNotSupportedError, UnmonitoredError
from .thresholds import validate, ThresholdManager, STREAM_FINISHED


class Manager:

    TAG = 'Manager'

    def __init__(self, dao, config: Config):
        self.config = config
        self.dao = dao
        self.kafka_manager = KafkaManager(config.kafka_bootstrap_server, config.kafka_call_list_topic)
        self.threshold_manager = ThresholdManager(config)
        # TODO: other managers for e.g. running ML predictions, retraining model etc.

    def start(self):
        asyncio.create_task(self._run())

    async def _run(self):
        kafka_producer = AIOKafkaProducer(bootstrap_servers=self.config.kafka_bootstrap_server)
        await kafka_producer.start()
        self.threshold_manager.init(kafka_producer)

        try:
            await asyncio.gather(
                self.threshold_manager.run(),
                self.kafka_manager.run(),
                self.bootstrap(),
                return_exceptions=True
            )
        finally:
            await kafka_producer.stop()

    async def bootstrap(self):
        await self.threshold_manager.started.wait()
        monitored = await self.dao.get_monitored_meetings()
        for meeting in monitored:
            await self.threshold_manager.schedule(meeting['name'], meeting['criteria'])
        logging.info(f'{self.TAG}: bootstrapped from {len(monitored)} meetings')

    async def schedule(self, conf_name: str, criteria: List[dict], monitoring_type: str):
        if monitoring_type == 'threshold':
            validate(criteria)

            await self.dao.set_monitoring_status(conf_name, monitored=True, criteria=criteria)
            await self.threshold_manager.schedule(conf_name, criteria)
            logging.info(f'{self.TAG}: scheduled monitoring for {conf_name}')
        else:
            raise MonitoringNotSupportedError()

    async def unschedule(self, conf_name: str, monitoring_type: str):
        if monitoring_type == 'threshold':
            await self.dao.set_monitoring_status(conf_name, monitored=False)
            await self.threshold_manager.unschedule(conf_name)
            logging.info(f'{self.TAG}: unscheduled monitoring for {conf_name}')
        else:
            raise MonitoringNotSupportedError()

    async def get_all_monitored(self):
        # TODO: test if DAO works
        monitored = await self.dao.get_monitored_meetings()
        return [meeting['name'] for meeting in monitored]

    async def is_monitored(self, conf_name: str):
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
        await self.threshold_manager.shutdown()
        logging.info(f'{self.TAG}: shutdown finished')


class KafkaManager:

    TAG = 'KafkaManager'

    def __init__(self, bootstrap_server, call_list_topic):
        self.bootstrap_server = bootstrap_server
        self.call_list_topic = call_list_topic
        self.call_event_listeners = set()
        self.anomaly_listeners = {}

        self.consumer = None

    async def run(self):
        self.consumer = AIOKafkaConsumer(
            self.call_list_topic, 'monitoring-anomalies', bootstrap_servers='kafka:29092',
        )
        await self.consumer.start()

        try:
            async for msg in self.consumer:
                msg_dict = json.loads(msg.value.decode())

                if msg.topic == self.call_list_topic:
                    call_name = msg_dict['meeting_name']
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
