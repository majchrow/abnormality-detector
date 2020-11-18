import logging
from aiohttp import web
from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster
from cassandra.query import dict_factory

from .config import Config


class CassandraDAO:
    def __init__(self, cluster, keyspace, call_info_table, roster_table, meetings_table):
        self.cluster = cluster
        self.keyspace = keyspace
        self.call_info_table = call_info_table
        self.roster_table = roster_table
        self.meetings_table = meetings_table
        self.session = None

    async def start(self):
        self.session = self.cluster.connect(self.keyspace)
        self.session.row_factory = dict_factory

    async def set_anomaly(self, call_id, datetime):
        logging.info(f'Saved anomaly for call {call_id} at {datetime}')

    async def shutdown(self):
        logging.info('Cassandra connection shutdown.')


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
