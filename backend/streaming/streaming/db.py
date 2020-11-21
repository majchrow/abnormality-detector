import asyncio
import json
import logging
from aiohttp import web
from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster
from cassandra.query import dict_factory
from typing import List

from .config import Config
from .exceptions import DBFailureError
from .monitoring.thresholds.criteria import Anomaly


# TODO:
#  - once we have more than just "threshold" monitoring we'll need to update methods below
#
class CassandraDAO:

    TAG = 'CassandraDAO'

    def __init__(self, cluster, keyspace, meetings_table, anomalies_table):
        self.cluster = cluster
        self.keyspace = keyspace
        self.meetings_table = meetings_table
        self.anomalies_table = anomalies_table
        self.session = None

    def start(self):
        self.session = self.cluster.connect(self.keyspace)
        self.session.row_factory = dict_factory

    def add_anomaly(self, meeting_name: str, datetime: str, anomalies: List[Anomaly]):
        reason = json.dumps([a.dict() for a in anomalies])
        future = self.session.execute_async(
            f'INSERT INTO {self.anomalies_table} (meeting_name, datetime, reason) '
            f'VALUES (%s, %s, %s);',
        (meeting_name, datetime, reason))

        future.add_callbacks(
            lambda _: logging.info(f'{self.TAG}: added anomaly for call {meeting_name} at {datetime}'),
            lambda e: logging.error(f'{self.TAG}: "add anomaly" for {meeting_name} at {datetime} failed with {e}')
        )

    def get_monitored_meetings(self):
        result = self.session.execute_async(
            f'SELECT meeting_name as name, criteria FROM {self.meetings_table} '
            f'WHERE monitored=true ALLOW FILTERING;'
        )

        loop = asyncio.get_running_loop()
        future = loop.create_future()

        def on_success(meetings):
            logging.info(f'{self.TAG}: fetched {len(meetings)} monitoring meetings'),
            future.set_result(meetings)

        def on_error(e):
            logging.error(f'{self.TAG}: "get monitored meetings" failed with {e}'),
            future.set_exception(
                DBFailureError(f'"get monitored meetings" failed with {e}')
            )

        result.add_callbacks(on_success, on_error)
        return future

    def set_monitoring_status(self, call_name: str, monitored: bool):
        result = self.session.execute_async(
            f'UPDATE {self.meetings_table} '
            f'SET monitored=%s '
            f'WHERE meeting_name=%s IF EXISTS;',
        (monitored, call_name))

        loop = asyncio.get_running_loop()
        future = loop.create_future()

        def on_success(_):
            logging.info(f'{self.TAG}: set monitoring status for call {call_name} to {monitored}'),
            future.set_result(None)

        def on_error(e):
            logging.error(f'{self.TAG}: "set monitoring status" for call {call_name} failed with {e}'),
            future.set_exception(
                DBFailureError(f'"set monitoring status" for {call_name} failed with {e}')
            )

        result.add_callbacks(on_success, on_error)
        return future

    async def shutdown(self):
        logging.info(f'{self.TAG}: connection shutdown.')


async def start_db(app: web.Application):
    app['db'].start()


async def cancel_db(app: web.Application):
    await app['db'].shutdown()


def setup_db(app, config: Config):
    auth_provider = PlainTextAuthProvider(username=config.cassandra_user, password=config.cassandra_passwd)
    cassandra = Cluster([config.cassandra_host], port=config.cassandra_port, auth_provider=auth_provider)
    dao = CassandraDAO(cassandra, config.keyspace, config.meetings_table, config.anomalies_table)
    app['db'] = dao
    app.on_startup.append(start_db)
    app.on_cleanup.append(cancel_db)
