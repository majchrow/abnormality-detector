import asyncio
import json
import logging
from aiohttp import web
from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster
from cassandra.query import dict_factory
from typing import List, Optional

from .config import Config
from .exceptions import DBFailureError, MeetingNotExistsError


# TODO:
#  - once we have more than just "threshold" monitoring we'll need to update methods below
#
class CassandraDAO:

    TAG = 'CassandraDAO'

    def __init__(self, cluster, keyspace, meetings_table):
        self.cluster = cluster
        self.keyspace = keyspace
        self.meetings_table = meetings_table
        self.session = None

    def start(self):
        self.session = self.cluster.connect(self.keyspace)
        self.session.row_factory = dict_factory

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

    async def shutdown(self):
        logging.info(f'{self.TAG}: connection shutdown.')


async def start_db(app: web.Application):
    app['db'].start()


async def cancel_db(app: web.Application):
    await app['db'].shutdown()


def setup_db(app, config: Config):
    auth_provider = PlainTextAuthProvider(username=config.cassandra_user, password=config.cassandra_passwd)
    cassandra = Cluster([config.cassandra_host], port=config.cassandra_port, auth_provider=auth_provider)
    dao = CassandraDAO(cassandra, config.keyspace, config.meetings_table)
    app['db'] = dao
    app.on_startup.append(start_db)
    app.on_cleanup.append(cancel_db)
