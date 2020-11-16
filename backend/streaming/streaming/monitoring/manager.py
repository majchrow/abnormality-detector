import asyncio
import json
import logging
from aiohttp import web
from aiokafka import AIOKafkaConsumer
from asyncio import Queue
from contextlib import contextmanager

from ..exceptions import MonitoringNotSupportedError, UnmonitoredError
from .thresholds import ThresholdManager


class Manager:

    TAG = 'Manager'

    def __init__(self, config):
        self.kafka_manager = KafkaManager(config.kafka_bootstrap_server, config.kafka_topic_map)
        self.threshold_manager = ThresholdManager(self.kafka_manager)
        # TODO: other managers for e.g. running ML predictions, retraining model etc.

    def start(self):
        self.kafka_manager.start()

    async def schedule(self, conf_name: str, request: dict):
        if request['type'] == 'threshold':
            self.threshold_manager.schedule(conf_name, request['criteria'])

    async def unschedule(self, conf_name: str, monitoring_type: str):
        if monitoring_type == 'threshold':
            await self.threshold_manager.unschedule(conf_name)

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

    def monitoring_receiver(self, call_name, monitoring_type: str):
        task = self.threshold_manager.monitoring_tasks.get(call_name, None)
        if not task:
            raise UnmonitoredError()
        if monitoring_type != 'threshold':
            raise MonitoringNotSupportedError()

        @contextmanager
        def _listen_manager():
            queue = Queue()

            async def _listen():
                task.subscribe(queue)
                while True:
                    msg = await queue.get()
                    if msg == ThresholdManager.STREAM_FINISHED:
                        break
                    yield msg

            try:
                yield _listen
            finally:
                task.unsubscribe(queue)

        return _listen_manager

    async def shutdown(self):
        await self.threshold_manager.shutdown()
        logging.info(f'{self.TAG}: shutdown finished')


class KafkaManager:

    TAG = 'KafkaManager'

    def __init__(self, bootstrap_server, input_topic_map):
        self.bootstrap_server = bootstrap_server
        self.task = None
        self.call_event_sinks = set()
        self.monitoring_event_sinks = {}
        self.input_topics = input_topic_map  # preprocessed output topic -> CMS event type

    def start(self):
        self.task = asyncio.create_task(self._run())

    async def stop(self):
        self.task.cancel()
        await self.task

    async def _run(self):
        topics = list(self.input_topics.keys())
        consumer = AIOKafkaConsumer(*topics, bootstrap_servers=self.bootstrap_server)

        await consumer.start()
        try:
            async for msg in consumer:
                msg_dict = json.loads(msg.value.decode())

                topic = self.input_topics[msg.topic]
                # TODO: message handling to separate method?
                if topic == 'callListUpdate':
                    call_name = msg_dict['name']
                    if msg_dict['finished']:
                        event = 'Meeting finished'
                    elif msg_dict['start_datetime'] == msg_dict['last_update']:
                        event = 'Meeting started'
                    else:
                        event = None
                    if event and self.call_event_sinks:
                        msg = {'name': call_name, 'event': event}
                        logging.info(f'pushing call info {msg} to {len(self.call_event_sinks)} subscribers')
                        for queue in self.call_event_sinks:
                            queue.put_nowait(msg)
                    continue

                if not (sinks := self.monitoring_event_sinks.get(msg_dict['name'], set())):
                    continue

                logging.info(f'{self.TAG}: pushing {msg_dict} from topic {topic} to {len(sinks)} monitors')
                for queue in sinks:
                    queue.put_nowait((topic, msg_dict))
        finally:
            await consumer.stop()

    def call_event_subscribe(self, queue):
        logging.info(f'{self.TAG}: registered call event subscriber')
        self.call_event_sinks.add(queue)

    def call_event_unsubscribe(self, queue):
        if queue in self.call_event_sinks:
            self.call_event_sinks.remove(queue)
            logging.info(f'{self.TAG}: unregistered call event subscriber')
        else:
            logging.info(f'{self.TAG}: "unsubscribe call events" attempt - subscriber not found')

    def monitoring_subscribe(self, conf_name: str, queue):
        logging.info(f'{self.TAG}: registered subscriber for {conf_name}')

        if (sinks := self.monitoring_event_sinks.get(conf_name, None)) is None:
            sinks = set()
            self.monitoring_event_sinks[conf_name] = sinks
        sinks.add(queue)

    def monitoring_unsubscribe(self, conf_name: str, queue):
        if not (sinks := self.monitoring_event_sinks.get(conf_name, None)):
            logging.warning(f'{self.TAG}: "unsubscribe" attempt for {conf_name} - conference unmonitored!')
        else:
            try:
                sinks.remove(queue)
                logging.info(f'{self.TAG}: unregistered subscriber for {conf_name}')
                if not sinks:
                    del self.monitoring_event_sinks[conf_name]
            except KeyError:
                logging.warning(f'{self.TAG}: "unsubscribe" attempt for {conf_name} - not a subscriber!')


async def start_all(app: web.Application):
    app['monitoring'].start()


async def cancel_all(app: web.Application):
    await app['monitoring'].shutdown()


def setup_monitoring(app: web.Application, config):
    manager = Manager(config)
    app['monitoring'] = manager
    app.on_startup.append(start_all)
    app.on_cleanup.append(cancel_all)
