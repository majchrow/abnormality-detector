import asyncio
import json
import logging
from aiohttp import web
from aiokafka import AIOKafkaProducer
from asyncio import Queue
from contextlib import contextmanager
from datetime import datetime, timedelta
from dateutil.parser import parse
from typing import List

from .kafka import KafkaEndpoint
from .serializers import DateTimeEncoder
from .subprocess import BaseWorkerManager, run_for_result
from .thresholds import STREAM_FINISHED, validate
from ..db import CassandraDAO
from ..config import Config
from ..exceptions import AppException


class Manager:

    TAG = 'Manager'

    def __init__(self, dao, config: Config):
        self.config = config
        self.dao = dao

        self.kafka_manager = KafkaEndpoint(config.kafka_bootstrap_server, config.kafka_call_list_topic)
        self.anomaly_manager = AnomalyManager(dao, self.kafka_manager, config)
        self.threshold_manager = ThresholdManager(dao, config)

    def start(self):
        asyncio.create_task(self._run())

    async def _run(self):
        kafka_producer = AIOKafkaProducer(bootstrap_servers=self.config.kafka_bootstrap_server)
        await kafka_producer.start()
        self.anomaly_manager.init(kafka_producer)
        self.kafka_manager.init(kafka_producer)
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
    async def schedule_training(self, meeting_name: str, calls: List[str], threshold: float, min_duration: int, max_participants: int):
        await self.anomaly_manager.train(meeting_name, calls, threshold)
        logging.info(f'{self.TAG}: scheduled model training for meeting {meeting_name} on calls {calls}')

        if min_duration is not None and max_participants is not None:
            await self.dao.set_retraining(meeting_name, min_duration, max_participants, threshold)
            logging.info(f'{self.TAG}: setup model retraining on {meeting_name} with threshold = {threshold} {max_participants} <= participants and {min_duration} <= duration')
        else:
            await self.dao.unset_retraining(meeting_name)
            logging.info(f'{self.TAG}: setup model retraining on {meeting_name} with threshold = {threshold} {max_participants} <= participants and {min_duration} <= duration')

    async def schedule_inference(self, meeting_name: str):
        await self.anomaly_manager.schedule(meeting_name)
        logging.info(f'{self.TAG}: scheduled inference for {meeting_name}')

    async def unschedule_inference(self, meeting_name: str):
        await self.anomaly_manager.unschedule(meeting_name)
        logging.info(f'{self.TAG}: unscheduled inference for {meeting_name}')

    async def run_inference(self, meeting_name: str, training_calls: List[datetime], start: datetime, end: datetime, threshold: float):
        await self.anomaly_manager.fire_anomaly(meeting_name, training_calls, start, end, threshold)
        logging.info(f'{self.TAG}: ran training & inference for {meeting_name}')

    async def is_anomaly_monitored(self, conf_name: str):
        return await self.dao.is_anomaly_monitored(conf_name)

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

    async def run_monitoring(self, meeting_name: str, criteria: List[dict], start: datetime, end: datetime):
        validate(criteria)
        await self.threshold_manager.fire_thresholds(meeting_name, criteria, start, end)
        logging.info(f'{self.TAG}: ran training & inference for {meeting_name}')

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
            self.kafka_manager.user_notifications_subscribe(queue)
            while True:
                msg = await queue.get()
                yield msg

        try:
            yield _listen
        finally:
            self.kafka_manager.user_notifications_unsubscribe(queue)

    async def monitoring_receiver(self, call_name):
        if not (await self.is_monitored(call_name)):
            raise AppException.not_monitored()

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

    def __init__(self, dao: CassandraDAO, config: Config):
        super().__init__()
        self.cmd = ['python3', '-m', 'streaming.monitoring.thresholds.monitor']
        self.num_workers = config.num_threshold_workers
        self.worker_id = 'thresholds-worker'
        self.dao = dao
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

    async def fire_thresholds(self, meeting_name, criteria, start, end):
        if not await self.dao.meeting_exists(meeting_name):
            raise AppException.meeting_not_found()

        payload = json.dumps({
            'meeting_name': meeting_name,
            'criteria': criteria,
            'start': start,
            'end': end,
        }, cls=DateTimeEncoder).encode()
        asyncio.create_task(run_for_result(
            'batch-thresholds-worker',
            ['python3', '-m', 'streaming.monitoring.thresholds.batch', payload]
        ))


def async_partial(coro_fun, *args, **kwargs):
    def run():
        return coro_fun(*args, **kwargs)
    return run


# Assumptions:
#  - when re-running old jobs, it may so happen that it gets completed multiple times (very
#    slow workers case), should not be an issue for now, might think of better tactic later
class AnomalyManager(BaseWorkerManager):

    TAG = 'AnomalyManager'

    def __init__(self, dao: CassandraDAO, kafka_endpoint: KafkaEndpoint, config: Config):
        super().__init__()
        self.dao = dao
        self.kafka_endpoint = kafka_endpoint
        self.kafka_producer = None
        self.dispatch_period = config.inference_period_s
        self.dispatch_task = None
        self.retrain_task = None

        self.cmd = ['python3', '-m', 'streaming.monitoring.anomalies.inference']
        self.num_workers = config.num_anomaly_workers
        self.worker_id = 'inference-worker'

    def init(self, kafka_producer):
        self.kafka_producer = kafka_producer

        dispatch_task = self._retry_on_failure(async_partial(self.periodic_dispatch), 'inference dispatch')
        self.dispatch_task = asyncio.create_task(dispatch_task)

        retrain_task = self._retry_on_failure(async_partial(self.retrain), 'automatic retraining')
        self.retrain_task = asyncio.create_task(retrain_task)

    async def _retry_on_failure(self, task, name):
        while True:
            try:
                await task()
                return
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logging.exception(f'{self.TAG}: {name} failed with {e}!')
                await asyncio.sleep(1)

    async def train(self, meeting_name, calls, threshold):
        if not await self.dao.meeting_exists(meeting_name):
            raise AppException.meeting_not_found()
        job_id = await self.dao.add_training_job(meeting_name, calls, threshold)
        # TODO:
        #  - kill worker on shutdown smh

        asyncio.create_task(run_for_result(
            'training-worker', ['python3', '-m', 'streaming.monitoring.anomalies.training', job_id]
        ))

    async def schedule(self, meeting_name):
        if not await self.dao.model_exists(meeting_name):
            raise AppException.model_not_found()
        if not await self.dao.set_anomaly_monitoring_status(meeting_name, True):
            raise AppException.meeting_not_found()
        await self.dao.add_inference_job(meeting_name, datetime.now(), datetime.now(), 'completed')

    async def unschedule(self, meeting_name):
        if not await self.dao.set_anomaly_monitoring_status(meeting_name, False):
            raise AppException.meeting_not_found()

    async def fire_anomaly(self, meeting_name, calls, start, end, threshold):
        if not await self.dao.set_anomaly_monitoring_status(meeting_name, True):
            raise AppException.meeting_not_found()

        job = {
            'meeting_name': meeting_name,
            'training_call_starts': calls,
            'start': start,
            'end': end,
            'threshold': threshold
        }
        payload = json.dumps(job, cls=DateTimeEncoder).encode()
        asyncio.create_task(run_for_result(
            'training-inference-worker',
            ['python3', '-m', 'streaming.monitoring.anomalies.training_inference', payload]
        ))

    async def periodic_dispatch(self):
        while True:
            await asyncio.sleep(self.dispatch_period)

            async with self.dao.try_lock('inference-schedule') as locked:
                if not locked:
                    logging.info(f'{self.TAG}: failed to obtain inference-schedule lock')
                    continue

                logging.info(f'{self.TAG}: obtained inference-schedule lock')
                monitored = await self.dao.get_anomaly_monitored_meetings()

                last_inferences = await self.dao.get_last_inferences(monitored)
                # add inference jobs for meetings with stale results
                now = datetime.now()
                jobs = []
                for inf in last_inferences:
                    if now - inf['end'] > timedelta(seconds=self.dispatch_period):
                        inf['start'], inf['end'] = inf['end'], now
                        jobs.append(inf)
                await asyncio.gather(*[self.dao.add_inference_job(**job) for job in jobs])
                if jobs:
                    logging.info(f'{self.TAG}: saved {len(jobs)} new inference jobs for {len(monitored)} meetings')
            logging.info(f'{self.TAG}: released inference-schedule lock')

            # actually schedule them (lock not necessary anymore)
            if jobs:
                await asyncio.gather(*map(self.push_inference_job, jobs))
                logging.info(f'{self.TAG}: pushed to workers')

    async def push_inference_job(self, job):
        payload = json.dumps(job, cls=DateTimeEncoder).encode()
        await self.kafka_producer.send_and_wait(topic='monitoring-anomalies-jobs', value=payload)

    async def retrain(self):
        queue = asyncio.Queue()

        try:
            self.kafka_endpoint.call_events_subscribe(queue)
            while True:
                msg = await queue.get()
                meeting_name, event = msg['meeting_name'], msg['event']
                if event != 'Meeting finished':
                    continue

                start_datetime, timestamp = parse(msg['start_datetime']).replace(tzinfo=None), parse(msg['datetime']).replace(tzinfo=None)

                if not (retraining := await self.dao.get_retraining(meeting_name)):
                    continue
                logging.info(f'{self.TAG}: retraining applicable to {meeting_name}...')

                async with self.dao.try_lock('retraining-update') as locked:
                    if not locked:
                        logging.info(f'{self.TAG}: failed to obtain retraining-update lock')
                        continue

                    if retraining['last_update'] and retraining['last_update'] >= timestamp:
                        logging.info(f'{self.TAG}: last retraining covered finished call')
                        continue
                    logging.info(f'{self.TAG}: last retraining till {retraining["last_update"]}')

                    await self.dao.update_retraining(meeting_name, timestamp)
                    logging.info(f'{self.TAG}: retraining updated on {timestamp}')

                duration, max_participants = await self.dao.get_call_details(meeting_name, start_datetime)
                if duration < retraining['min_duration'] or max_participants < retraining['max_participants']:
                    continue
                logging.info(f'{self.TAG}: duration: {duration}, max_participants: {max_participants}')

                if (model := await self.dao.get_model(meeting_name)) and start_datetime in model['training_call_starts']:
                    logging.info(f'{self.TAG}: model already trained on last call!')
                    continue
                
                logging.info(f'{self.TAG}: launching retraining...')
                calls = [start_datetime] + (model['training_call_starts'] if model else [])
                await self.train(meeting_name, calls, retraining['threshold'])
        except Exception as e:
            raise e
        finally:
            self.kafka_endpoint.call_events_unsubscribe(queue)

    async def shutdown(self):
        await super().shutdown()

        self.dispatch_task.cancel()
        await self.dispatch_task


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
