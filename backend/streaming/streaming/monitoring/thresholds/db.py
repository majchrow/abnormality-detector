import pandas as pd
from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster, dict_factory
from cassandra.concurrent import execute_concurrent_with_args
from cassandra.query import ValueSequence

from ...config import Config


class CassandraDAO:
    def __init__(self, session):
        self.session = session

    def load_data(self, meeting_name, start, end):
        calls_result = self.session.execute(
            f'SELECT * FROM calls '
            f'WHERE meeting_name = %s AND last_update >= %s AND last_update <= %s ALLOW FILTERING;',
            (meeting_name, start, end)
        ).all()

        ci_result = self.session.execute(
            f'SELECT * FROM call_info_update '
            f'WHERE meeting_name = %s AND datetime >= %s AND datetime <= %s;',
            (meeting_name, start, end)
        ).all()

        roster_result = self.session.execute(
            f'SELECT * FROM roster_update '
            f'WHERE meeting_name = %s AND datetime >= %s AND datetime <= %s;',
            (meeting_name, start, end)
        ).all()

        return calls_result, ci_result, roster_result

    def save_anomaly_status(self, call_results, ci_results, roster_results):
        if call_results:
            call_stmt = self.session.prepare(
                f"UPDATE calls "
                f"SET anomaly=?, anomaly_reason=?"
                f"WHERE meeting_name=? AND start_datetime=?;"
            )
            execute_concurrent_with_args(self.session, call_stmt, call_results)
        if ci_results:
            ci_stmt = self.session.prepare(
                f"UPDATE call_info_update "
                f"SET anomaly=?, anomaly_reason=?"
                f"WHERE meeting_name=? AND datetime=?;"
            )
            execute_concurrent_with_args(self.session, ci_stmt, ci_results)
        if roster_results:
            roster_stmt = self.session.prepare(
                f"UPDATE roster_update "
                f"SET anomaly=?, anomaly_reason=? "
                f"WHERE meeting_name=? AND datetime=?;"
            )
            execute_concurrent_with_args(self.session, roster_stmt, roster_results)


def build_dao(config: Config):
    auth_provider = PlainTextAuthProvider(username=config.cassandra_user, password=config.cassandra_passwd)
    cassandra = Cluster([config.cassandra_host], port=config.cassandra_port, auth_provider=auth_provider)
    session = cassandra.connect(config.keyspace)
    session.row_factory = dict_factory

    return CassandraDAO(session)
