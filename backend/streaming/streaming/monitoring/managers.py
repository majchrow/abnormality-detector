import asyncio
import json
import logging
from aiohttp import web
from aiokafka import AIOKafkaProducer
from asyncio import Queue
from contextlib import contextmanager
from typing import List

from ..config import Config
from ..exceptions import MonitoringNotSupportedError, UnmonitoredError
from .kafka import KafkaListener
from .thresholds import validate, STREAM_FINISHED
from .subprocess import BaseWorkerManager, run_for_result


class Manager:

    TAG = 'Manager'

    def __init__(self, dao, config: Config):
        self.config = config
        self.dao = dao

        self.anomaly_manager = AnomalyManager(config)
        self.kafka_manager = KafkaListener(config.kafka_bootstrap_server, config.kafka_call_list_topic)
        self.threshold_manager = ThresholdManager(config)
        # TODO: other managers for e.g. running ML predictions, retraining model etc.

    def start(self):
        asyncio.create_task(self._run())

    async def _run(self):
        kafka_producer = AIOKafkaProducer(bootstrap_servers=self.config.kafka_bootstrap_server)
        await kafka_producer.start()
        self.anomaly_manager.init(kafka_producer)
        self.threshold_manager.init(kafka_producer)

        try:
            await asyncio.gather(
                self.anomaly_manager.run(),
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
        elif monitoring_type == 'anomaly':
            await self.anomaly_manager.schedule(conf_name, 'HBOS')
            logging.info(f'{self.TAG}: scheduled monitoring for {conf_name}')
        else:
            raise MonitoringNotSupportedError()

    async def unschedule(self, conf_name: str, monitoring_type: str):
        if monitoring_type == 'threshold':
            await self.dao.set_monitoring_status(conf_name, monitored=False)
            await self.threshold_manager.unschedule(conf_name)
            logging.info(f'{self.TAG}: unscheduled monitoring for {conf_name}')
        elif monitoring_type == 'anomaly':
            await self.anomaly_manager.unschedule(conf_name)
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


class ThresholdManager(BaseWorkerManager):

    TAG = 'ThresholdManager'

    def __init__(self, config: Config):
        super().__init__()
        self.cmd = ['python3', '-m', 'streaming.monitoring.thresholds.monitor']
        self.num_workers = config.num_workers  # TODO: separate for thresholds and anomalies
        self.worker_id = 'thresholds-worker'
        self.kafka_producer = None

    def init(self, kafka_producer):
        self.kafka_producer = kafka_producer

    async def schedule(self, meeting_name, criteria):
        payload = json.dumps({
            'type': 'update',
            'meeting_name': meeting_name,
            'criteria': criteria
        }).encode()
        await self.kafka_producer.send_and_wait(topic='monitoring-thresholds-config', value=payload)

    async def unschedule(self, meeting_name):
        payload = json.dumps({
            'type': 'delete',
            'meeting_name': meeting_name
        }).encode()
        await self.kafka_producer.send_and_wait(topic='monitoring-thresholds-config', value=payload)


class AnomalyManager(BaseWorkerManager):

    TAG = 'AnomalyManager'

    def __init__(self, config: Config):
        super().__init__()
        self.cmd = ['python3', '-m', 'streaming.monitoring.anomalies.inference']
        self.num_workers = config.num_workers  # TODO: separate for thresholds and anomalies
        self.worker_id = 'inference-worker'
        self.kafka_producer = None

    def init(self, kafka_producer):
        self.kafka_producer = kafka_producer

    async def schedule(self, meeting_name, model):
        payload = json.dumps({
            'type': 'schedule',
            'meeting_name': meeting_name,
            'model': model
        }).encode()
        await self.kafka_producer.send_and_wait(topic='monitoring-anomalies-config', value=payload)

    async def unschedule(self, meeting_name):
        payload = json.dumps({
            'type': 'unschedule',
            'meeting_name': meeting_name
        }).encode()
        await self.kafka_producer.send_and_wait(topic='monitoring-anomalies-config', value=payload)

    async def train(self, meeting_name, model, calls):
        await run_for_result(
            'training-worker',
            ['python3', '-m', 'streaming.monitoring.anomalies.training', meeting_name, model, *calls]
        )


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
