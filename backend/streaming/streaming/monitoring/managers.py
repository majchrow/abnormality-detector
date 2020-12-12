import asyncio
import json
import logging
from aiohttp import web
from aiokafka import AIOKafkaProducer
from asyncio import Queue
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import List

from .kafka import KafkaListener
from .thresholds import STREAM_FINISHED, validate
from .subprocess import BaseWorkerManager, run_for_result
from ..db import CassandraDAO
from ..config import Config
from ..exceptions import MeetingNotExistsError, ModelNotExistsError, MonitoredAlreadyError, UnmonitoredError


class Manager:

    TAG = 'Manager'

    def __init__(self, dao, config: Config):
        self.config = config
        self.dao = dao

        self.anomaly_manager = AnomalyManager(dao, config)
        self.kafka_manager = KafkaListener(config.kafka_bootstrap_server, config.kafka_call_list_topic)
        self.threshold_manager = ThresholdManager(config)

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
                return_exceptions=True
            )
        finally:
            await kafka_producer.stop()

    ###################
    # anomaly detection
    ###################
    async def schedule_training(self, meeting_name: str, calls: List[str]):
        await self.anomaly_manager.train(meeting_name, calls)
        logging.info(f'{self.TAG}: scheduled model training for meeting {meeting_name} on calls {calls}')

    async def schedule_inference(self, meeting_name: str):
        await self.anomaly_manager.schedule(meeting_name)
        logging.info(f'{self.TAG}: scheduled inference for {meeting_name}')

    async def unschedule_inference(self, meeting_name: str):
        await self.anomaly_manager.unschedule(meeting_name)
        logging.info(f'{self.TAG}: unscheduled inference for {meeting_name}')

    ############
    # monitoring
    ############
    async def schedule_monitoring(self, meeting_name: str, criteria: List[dict]):
        validate(criteria)
        await self.dao.set_monitoring_status(meeting_name, monitored=True, criteria=criteria)
        await self.threshold_manager.schedule(meeting_name, criteria)
        logging.info(f'{self.TAG}: scheduled monitoring for {meeting_name}')

    async def unschedule_monitoring(self, meeting_name: str):
        await self.dao.set_monitoring_status(meeting_name, monitored=False)
        await self.threshold_manager.unschedule(meeting_name)
        logging.info(f'{self.TAG}: unscheduled monitoring for {meeting_name}')

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

    async def monitoring_receiver(self, call_name):
        if not (await self.is_monitored(call_name)):
            raise UnmonitoredError()

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
        await self.anomaly_manager.shutdown()
        logging.info(f'{self.TAG}: shutdown finished')


class ThresholdManager(BaseWorkerManager):

    TAG = 'ThresholdManager'

    def __init__(self, config: Config):
        super().__init__()
        self.cmd = ['python3', '-m', 'streaming.monitoring.thresholds.monitor']
        self.num_workers = config.num_threshold_workers
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


# TODO:
#  - idea:
#    - pool of long-running workers
#    - "anomaly_monitored" and "last_update" columns in "meetings" table
#    - so state of all anomaly monitoring is persisted
#    - periodically:
#      - query the DB (with lock)
#      - find meetings with old last_update (configurable, say 1 minute)
#      - push jobs to Kafka
#      - unlock the DB
#    - also, no "schedule" and "delete" - don't keep any state in the worker (state in DB, not in memory pls)

# Assumptions:
#  - when re-running old jobs, it may so happen that it gets completed multiple times (very
#    slow workers case), should not be an issue for now, might think of better tactic later
class AnomalyManager(BaseWorkerManager):

    TAG = 'AnomalyManager'

    def __init__(self, dao: CassandraDAO, config: Config):
        super().__init__()
        self.dao = dao
        self.kafka_producer = None

        self.cmd = ['python3', '-m', 'streaming.monitoring.anomalies.inference']
        self.num_workers = config.num_anomaly_workers
        self.worker_id = 'inference-worker'

    def init(self, kafka_producer):
        self.kafka_producer = kafka_producer
        # TODO: keep reference to kill on shutdown
        asyncio.create_task(self.periodic_dispatch())

    async def train(self, meeting_name, calls):
        job_id = await self.dao.add_training_job(meeting_name, calls)
        # TODO:
        #  - indicate it's by call start datetime
        #  - kill worker on shutdown smh

        asyncio.create_task(run_for_result(
            'training-worker', ['python3', '-m', 'streaming.monitoring.anomalies.training', job_id]
        ))

    async def schedule(self, meeting_name):
        if not await self.dao.set_anomaly_monitoring_status(meeting_name, True):
            raise MeetingNotExistsError
        await self.dao.add_inference_job(meeting_name, datetime.now(), datetime.now(), 'completed')

    async def unschedule(self, meeting_name):
        if not await self.dao.set_anomaly_monitoring_status(meeting_name, False):
            raise MeetingNotExistsError

    async def periodic_dispatch(self):
        while True:
            async with self.dao.try_lock('inference-schedule') as locked:
                if not locked:
                    logging.info(f'{self.TAG}: failed to obtain inference-schedule lock')
                    await asyncio.sleep(5)  # TODO: make configurable
                    continue

                logging.info(f'{self.TAG}: obtained inference-schedule lock')
                monitored = await self.dao.get_anomaly_monitored_meetings()
                last_inferences = await self.dao.get_last_inferences(monitored)

                await asyncio.sleep(5)
                # add inference jobs for meetings with stale results
                now = datetime.now()
                jobs = []
                for inf in last_inferences:
                    if now - inf['end'] > timedelta(seconds=1):  # TODO: make configurable
                        inf['start'], inf['end'] = inf['end'], now
                        jobs.append(inf)
                logging.info(str(jobs))
                await asyncio.gather(*[self.dao.add_inference_job(**job) for job in jobs])

            logging.info(f'{self.TAG}: released inference-schedule lock')

            for job in jobs:
                job['start'] = job['start'].strftime('%Y-%m-%d %H:%M:%S.%fZ')
                job['end'] = job['end'].strftime('%Y-%m-%d %H:%M:%S.%fZ')
            # actually schedule them (lock not necessary anymore)
            kafka_jobs = [
                self.kafka_producer.send_and_wait(topic='monitoring-anomalies-jobs', value=json.dumps(job).encode())
                for job in jobs
            ]
            await asyncio.gather(*kafka_jobs)
            await asyncio.sleep(5)  # TODO: make configurable

    async def periodic_cleanup(self):
        # TODO:
        #  - remove stale locks (what if process fails while holding a lock??)
        #  - re-run old and still not completed jobs
        pass


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
