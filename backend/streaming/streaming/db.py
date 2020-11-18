import logging
from aiohttp import web
from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster
from cassandra.query import dict_factory

from .config import Config


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

    # TODO: is it inserted as datetime?
    async def set_anomaly(self, call_id: str, datetime: str, topic):
        table = self.call_info_table if topic == 'callInfoUpdate' else self.roster_table
        future = self.session.execute_async(
            f'UPDATE {table} '
            f'SET anomaly=true '
            f'WHERE call_id=%s AND datetime=%s;',
        (call_id, datetime))

        future.add_callbacks(
            lambda _: logging.info(f'{self.TAG}: set anomaly status for call {call_id} at {datetime}'),
            lambda e: logging.error(f'{self.TAG}: set anomaly status for {call_id} at {datetime} failed with {e}')
        )

    async def set_monitoring_status(self, call_name: str,):
        # TODO
        pass

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
