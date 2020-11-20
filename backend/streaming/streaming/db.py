import asyncio
import logging
from aiohttp import web
from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster
from cassandra.query import dict_factory

from .config import Config
from .exceptions import DBFailureError


# TODO:
#  - once we have more than just "threshold" monitoring we'll need to update methods below
#
class CassandraDAO:

    TAG = 'CassandraDAO'

    def __init__(self, cluster, keyspace, call_info_table, roster_table, meetings_table):
        self.cluster = cluster
        self.keyspace = keyspace
        self.call_info_table = call_info_table
        self.roster_table = roster_table
        self.meetings_table = meetings_table
        self.session = None

    def start(self):
        self.session = self.cluster.connect(self.keyspace)
        self.session.row_factory = dict_factory

    def set_anomaly(self, call_id: str, datetime: str, topic):
        table = self.call_info_table if topic == 'callInfoUpdate' else self.roster_table
        future = self.session.execute_async(
            f'UPDATE {table} '
            f'SET anomaly=true '
            f'WHERE call_id=%s AND datetime=%s IF EXISTS;',
        (call_id, datetime))

        future.add_callbacks(
            lambda _: logging.info(f'{self.TAG}: set anomaly status for call {call_id} at {datetime}'),
            lambda e: logging.error(f'{self.TAG}: set anomaly status for {call_id} at {datetime} failed with {e}')
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
    dao = CassandraDAO(cassandra, config.keyspace, config.call_info_table, config.roster_table, config.meetings_table)
    app['db'] = dao
    app.on_startup.append(start_db)
    app.on_cleanup.append(cancel_db)
