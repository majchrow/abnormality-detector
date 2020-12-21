import asyncio
import json
import logging
from aiohttp import web
from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster
from cassandra.query import dict_factory
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from .config import Config
from .exceptions import AppException


class CassandraDAO:

    TAG = 'CassandraDAO'

    def __init__(self, cluster, config):
        self.cluster = cluster
        self.keyspace = config.keyspace
        self.meetings_table = config.meetings_table
        self.training_jobs_table = config.training_jobs_table
        self.models_table = config.models_table
        self.session = None

    def start(self):
        self.session = self.cluster.connect(self.keyspace)
        self.session.row_factory = dict_factory

    async def async_exec(self, name, query, args=None):
        def callback(result):
            if result is not None:
                result = list(result)
            future.set_result(result)

        def errback(e):
            logging.error(f'{self.TAG}: "{name}" failed with {e}'),
            future.set_exception(AppException.db_error())

        loop = asyncio.get_running_loop()
        future = loop.create_future()

        if args:
            promise = self.session.execute_async(query, args)
        else:
            promise = self.session.execute_async(query)

        promise.add_callbacks(callback, errback)
        return await future

    ############
    # thresholds
    ############
    async def get_monitored_meetings(self):
        meetings = await self.async_exec(
            'get_monitored_meetings',
            f'SELECT meeting_name as name, criteria FROM {self.meetings_table} '
            f'WHERE monitored=true ALLOW FILTERING;'
        )
        logging.info(f'{self.TAG}: fetched {len(meetings)} monitoring meetings')
        for m in meetings:
            m['criteria'] = json.loads(m['criteria'])
        return meetings

    async def is_monitored(self, call_name: str):
        result = await self.async_exec(
            'is_monitored',
            f'SELECT monitored FROM {self.meetings_table} '
            f'WHERE meeting_name=%s;',
            (call_name,)
        )
        logging.info(f'{self.TAG}: fetched monitoring status for {call_name}')
        return result[0]['monitored'] if result else False

    async def set_monitoring_status(self, call_name: str, monitored: bool, criteria: Optional[List[dict]] = None):
        if criteria is None:
            result = await self.async_exec(
                'set_monitoring_status',
                f'UPDATE {self.meetings_table} '
                f'SET monitored=%s '
                f'WHERE meeting_name=%s IF EXISTS;',
                (monitored, call_name)
            )
        else:
            result = await self.async_exec(
                'set_monitoring_status',
                f'UPDATE {self.meetings_table} '
                f'SET monitored=%s, criteria=%s '
                f'WHERE meeting_name=%s IF EXISTS;',
                (monitored, json.dumps(criteria), call_name)
            )
        if result[0]['[applied]']:
            logging.info(f'{self.TAG}: set monitoring status for call {call_name} to {monitored}')
        else:
            logging.info(f'"set monitoring status" ignored - {call_name} does not exist')
            raise AppException.meeting_not_found()

    ###################
    # anomaly detection
    ###################
    async def is_anomaly_monitored(self, call_name: str):
        result = await self.async_exec(
            'is_anomaly_monitored',
            f'SELECT ml_monitored FROM {self.meetings_table} '
            f'WHERE meeting_name=%s;',
            (call_name,)
        )
        logging.info(f'{self.TAG}: fetched ML monitoring status for {call_name}')
        if result and result[0]['ml_monitored']:
            return True
        return False

    async def add_training_job(self, meeting_name: str, calls: List[str], threshold: float):
        uid = str(uuid4())
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        await self.async_exec(
            'add_training_job',
            f"INSERT INTO training_jobs (job_id, meeting_name, submission_datetime, training_call_starts, threshold, status) "
            f"VALUES (%s, %s, %s, %s, %s, %s);",
            (uid, meeting_name, now, calls, threshold, 'pending')
        )
        logging.info(f'{self.TAG}: added training job for {meeting_name} on {calls}')
        return uid

    async def set_retraining(self, meeting_name: str, min_duration: int, max_participants: int, threshold: float):
        await self.async_exec(
            'set_retraining',
            f"INSERT INTO retraining (meeting_name, min_duration, max_participants, threshold) "
            f"VALUES (%s, %s, %s, %s);",
            (meeting_name, min_duration, max_participants, threshold)
        )
        logging.info(f'{self.TAG}: retraining set for {meeting_name} with {threshold} threshold {min_duration} duration '
                     f'and {max_participants} participants')

    async def get_retraining(self, meeting_name):
        result = await self.async_exec(
            'get_retraining',
            f'SELECT * FROM retraining '
            f'WHERE meeting_name=%s;',
            (meeting_name,)
        )
        return {
            'min_duration': result[0]['min_duration'],
            'max_participants': result[0]['max_participants'],
            'last_update': result[0]['last_update'],
            'threshold': result[0]['threshold']
        } if result else None

    async def update_retraining(self, meeting_name, timestamp):
        await self.async_exec(
            'update_retraining',
            f'UPDATE retraining '
            f'SET last_update=%s '
            f'WHERE meeting_name=%s IF EXISTS;',
            (timestamp, meeting_name)
        )

    async def get_call_details(self, meeting_name, start_datetime):
        result_dur = (await self.async_exec(
            'get_call_duration',
            f'SELECT duration, last_update FROM calls '
            f'WHERE meeting_name=%s AND start_datetime=%s;',
            (meeting_name, start_datetime)
        ))[0]
        duration = result_dur['duration']

        result_mp = await self.async_exec(
            'get_call_duration',
            f'SELECT MAX(max_participants) AS mp FROM call_info_update '
            f'WHERE meeting_name=%s AND datetime >= %s AND datetime <= %s;',
            (meeting_name, start_datetime, result_dur['last_update'])
        )
        max_participants = result_mp[0]['mp'] if result_mp else 0
        return duration, max_participants

    async def get_model(self, meeting_name):
        result_model = await self.async_exec(
            'get_model',
            f'SELECT training_call_starts, threshold FROM models '
            f'WHERE meeting_name=%s;',
            (meeting_name,)
        )
        return result_model[0] if result_model else None

    async def meeting_exists(self, meeting_name):
        result = await self.async_exec(
            'meeting_exists',
            f'SELECT * FROM meetings '
            f'WHERE meeting_name=%s '
            f'LIMIT 1;',
            (meeting_name,)
        )
        return bool(result)

    async def model_exists(self, meeting):
        result = await self.async_exec(
            'model_exists',
            f'SELECT * FROM models '
            f'WHERE meeting_name=%s '
            f'LIMIT 1;',
            (meeting,)
        )
        return bool(result)

    async def set_anomaly_monitoring_status(self, meeting_name, status):
        # TODO: races (lock again?)
        result = await self.async_exec(
            'set_anomaly_monitoring_status',
            f'UPDATE meetings '
            f'SET ml_monitored=%s '
            f'WHERE meeting_name=%s '
            f'IF EXISTS;',
            (status, meeting_name)
        )
        return result[0]['[applied]'] if result else False

    async def get_anomaly_monitored_meetings(self):
        result = await self.async_exec(
            'get_anomaly_monitored_meetings',
            f'SELECT meeting_name FROM meetings '
            f'WHERE ml_monitored=true ALLOW FILTERING;'
        )
        return [m['meeting_name'] for m in result]

    async def get_last_inferences(self, monitored_meetings):
        # TODO: use execute_concurrent?
        jobs = [self.async_exec(
            'get_last_inferences',
            f'SELECT meeting_name, end_datetime as end '
            f'FROM inference_jobs '
            f'WHERE meeting_name=%s '
            f'ORDER BY end_datetime DESC '
            f'LIMIT 1;',
            (meeting,)
        ) for meeting in monitored_meetings]
        results = await asyncio.gather(*jobs)
        return [res[0] for res in results if res]

    async def earliest_observation(self, meeting_name):
        ci_result = await self.async_exec(
            'earliest_call_info_observation',
            f'SELECT datetime FROM call_info_update '
            f'WHERE meeting_name=%s '
            f'ORDER BY datetime ASC LIMIT 1;',
            (meeting_name,)
        )
        roster_result = await self.async_exec(
            'earliest_call_info_observation',
            f'SELECT datetime FROM roster_update '
            f'WHERE meeting_name=%s '
            f'ORDER BY datetime ASC LIMIT 1;',
            (meeting_name,)
        )
        return min(roster_result[0]['datetime'], ci_result[0]['datetime'])

    async def add_inference_job(self, meeting_name, start, end, status='pending'):
        await self.async_exec(
            'add_inference_job',
            f"INSERT INTO inference_jobs (meeting_name, start_datetime, end_datetime, status) "
            f"VALUES (%s, %s, %s, %s);",
            (meeting_name, start, end, status)
        )

    @asynccontextmanager
    async def try_lock(self, resource):
        try:
            # lock using Cassandra's lightweight transactions
            now = datetime.now()
            uid = str(uuid4())
            result = await self.async_exec(
                'try_lock',
                f'UPDATE locks SET lock_id=%s, last_locked=%s '
                f'WHERE resource_name=%s '
                f'IF lock_id=null;',
                (uid, now, resource)
            )
            yield result[0]['[applied]']
        finally:
            await self.async_exec(
                'try_lock',
                'UPDATE locks SET lock_id=null '
                'WHERE resource_name=%s;',
                (resource,)
            )

    async def shutdown(self):
        logging.info(f'{self.TAG}: connection shutdown.')


async def start_db(app: web.Application):
    app['db'].start()


async def cancel_db(app: web.Application):
    await app['db'].shutdown()


def setup_db(app, config: Config):
    auth_provider = PlainTextAuthProvider(username=config.cassandra_user, password=config.cassandra_passwd)
    cassandra = Cluster([config.cassandra_host], port=config.cassandra_port, auth_provider=auth_provider)
    dao = CassandraDAO(cassandra, config)
    app['db'] = dao
    app.on_startup.append(start_db)
    app.on_cleanup.append(cancel_db)
