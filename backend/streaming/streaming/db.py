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
from .exceptions import DBFailureError, MeetingNotExistsError, MonitoredAlreadyError


# TODO:
#  - once we have more than just "threshold" monitoring we'll need to update methods below
#
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

    async def async_exec(self, query, args=None):
        def callback(result):
            future.set_result(result)

        def errback(e):
            future.set_exception(e)

        if args:
            promise = self.session.execute_async(query, args)
        else:
            promise = self.session.execute_async(query)
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        promise.add_callbacks(callback, errback)
        return await future

    def get_monitored_meetings(self):
        result = self.session.execute_async(
            f'SELECT meeting_name as name, criteria FROM {self.meetings_table} '
            f'WHERE monitored=true ALLOW FILTERING;'
        )

        loop = asyncio.get_running_loop()
        future = loop.create_future()

        def on_success(meetings):
            logging.info(f'{self.TAG}: fetched {len(meetings)} monitoring meetings')
            for m in meetings:
                m['criteria'] = json.loads(m['criteria'])
            future.set_result(meetings)

        def on_error(e):
            logging.error(f'{self.TAG}: "get monitored meetings" failed with {e}'),
            future.set_exception(
                DBFailureError(f'"get monitored meetings" failed with {e}')
            )

        result.add_callbacks(on_success, on_error)
        return future

    def is_monitored(self, call_name: str):
        result = self.session.execute_async(
            f'SELECT monitored FROM {self.meetings_table} '
            f'WHERE meeting_name=%s;',
            (call_name,)
        )

        loop = asyncio.get_running_loop()
        future = loop.create_future()

        def on_success(result):
            logging.info(f'{self.TAG}: fetched monitoring status for {call_name}')
            status = result[0]['monitored'] if result else False
            future.set_result(status)

        def on_error(e):
            logging.error(f'{self.TAG}: "is monitored" failed with {e}'),
            future.set_exception(
                DBFailureError(f'"is monitored" failed with {e}')
            )

        result.add_callbacks(on_success, on_error)
        return future

    def set_monitoring_status(self, call_name: str, monitored: bool, criteria: Optional[List[dict]]=None):
        if criteria is None:
            result = self.session.execute_async(
                f'UPDATE {self.meetings_table} '
                f'SET monitored=%s '
                f'WHERE meeting_name=%s IF EXISTS;', 
            (monitored, call_name))
        else:
            result = self.session.execute_async(
                f'UPDATE {self.meetings_table} '
                f'SET monitored=%s, criteria=%s'
                f'WHERE meeting_name=%s IF EXISTS;', 
            (monitored, json.dumps(criteria), call_name))

        loop = asyncio.get_running_loop()
        future = loop.create_future()

        def on_success(response):
            applied = response[0]['[applied]']
            if applied:
                logging.info(f'{self.TAG}: set monitoring status for call {call_name} to {monitored}')
                future.set_result(None)
            else:
                logging.info(f'"set monitoring status" ignored - {call_name} does not exist')
                future.set_exception(MeetingNotExistsError())

        def on_error(e):
            logging.error(f'{self.TAG}: "set monitoring status" for call {call_name} failed with {e}'),
            future.set_exception(
                DBFailureError(f'"set monitoring status" for {call_name} failed with {e}')
            )

        result.add_callbacks(on_success, on_error)
        return future

    def add_training_job(self, meeting_name: str, calls: List[str]):
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        result = self.session.execute_async(
            f"INSERT INTO {self.training_jobs_table} (meeting_name, training_calls, submission_datetime, status) "
            f"VALUES (%s, %s, %s, %s);",
            (meeting_name, calls, now, 'pending')
        )

        loop = asyncio.get_running_loop()
        future = loop.create_future()

        def on_success(_):
            logging.info(f'{self.TAG}: added training job for {meeting_name} on {calls}')
            future.set_result(now)

        def on_error(e):
            logging.error(f'{self.TAG}: "add training job" failed with {e}'),
            future.set_exception(
                DBFailureError(f'"add training job" failed with {e}')
            )

        result.add_callbacks(on_success, on_error)
        return future

    async def meeting_exists(self, meeting_name):
        result = await self.async_exec(
            f'SELECT * FROM meetings '
            f'WHERE meeting_name=%s '
            f'LIMIT 1;',
            (meeting_name,)
        )
        return bool(list(result))

    async def model_exists(self, model_id):
        result = await self.async_exec(
            f'SELECT * FROM models '
            f'WHERE model_id=%s '
            f'LIMIT 1;',
            (model_id,)
        )
        return bool(list(result))

    async def get_anomaly_monitoring_status(self, meeting_name):
        result = await self.async_exec(
            f'SELECT model_id, monitored '
            f'FROM anomaly_monitoring '
            f'WHERE meeting_name=%s;',
            (meeting_name,)
        )
        return list(result)

    async def get_anomaly_monitoring_instance(self, meeting_name, model_id):
        result = list(await self.async_exec(
            f'SELECT monitored '
            f'FROM anomaly_monitoring '
            f'WHERE meeting_name=%s AND model_id=%s;',
            (meeting_name, model_id)
        ))
        return result[0] if result else None

    async def set_anomaly_monitoring_status(self, meeting_name, model_id, status):
        # TODO: races (lock again?)
        await self.async_exec(
            f'INSERT INTO anomaly_monitoring(meeting_name, model_id, monitored) '
            f'VALUES (%s, %s, %s);',
            (meeting_name, model_id, status)
        )

    async def get_anomaly_monitored_meetings(self):
        return await self.async_exec(
            f'SELECT meeting_name, model_id FROM anomaly_monitoring '
            f'WHERE monitored=true ALLOW FILTERING;'
        )

    async def get_last_inferences(self, monitored_meetings):
        # TODO: use execute_concurrent?
        jobs = [self.async_exec(
            f'SELECT meeting_name, model_id, end_datetime as end '
            f'FROM inference_jobs '
            f'WHERE meeting_name=%s AND model_id=%s '
            f'ORDER BY end_datetime DESC '
            f'LIMIT 1;',
            (m['meeting_name'], m['model_id'])
        ) for m in monitored_meetings]
        results = await asyncio.gather(*jobs)
        return [res[0] for res in results if res]

    async def add_inference_job(self, meeting_name, model_id, start, end):
        await self.async_exec(
            f"INSERT INTO inference_jobs (meeting_name, model_id, start_datetime, end_datetime, status) "
            f"VALUES (%s, %s, %s, %s, %);",
            (meeting_name, model_id, start, end, 'pending')
        )

    @asynccontextmanager
    async def try_lock(self, resource):
        try:
            # lock using Cassandra's lightweight transactions
            uid = str(uuid4())
            result = await self.async_exec(
                f'UPDATE locks SET lock_id=%s '
                f'WHERE resource_name=%s '
                f'IF lock_id=null;',
                (uid, resource)
            )
            yield next(iter(result))['[applied]']
        finally:
            await self.async_exec(
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
