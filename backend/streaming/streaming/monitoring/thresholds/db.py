import pandas as pd
from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster, dict_factory
from cassandra.concurrent import execute_concurrent_with_args
from cassandra.query import ValueSequence
from itertools import repeat

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
            meeting_name = ci_results[0][1]
            ci_stmt = self.session.prepare(
                f"UPDATE call_info_update "
                f"SET anomaly_reason=?"
                f"WHERE meeting_name=? AND datetime=?;"
            )
            execute_concurrent_with_args(self.session, ci_stmt, ci_results)
            self.fix_anomaly_status('call_info_update', meeting_name, [r[2] for r in ci_results])
        if roster_results:
            meeting_name = roster_results[0][1]
            roster_stmt = self.session.prepare(
                f"UPDATE roster_update "
                f"SET anomaly_reason=? "
                f"WHERE meeting_name=? AND datetime=?;"
            )
            execute_concurrent_with_args(self.session, roster_stmt, roster_results)
            self.fix_anomaly_status('roster_update', meeting_name, [r[2] for r in roster_results])

    def fix_anomaly_status(self, table, meeting_name, timestamps):
        # TODO: with lock...
        result_reasons = self.session.execute(
            f'SELECT anomaly_reason, ml_anomaly_reason FROM {table} '
            f'WHERE meeting_name = %s AND datetime IN %s;',
            (meeting_name, ValueSequence(timestamps))
        ).all()

        status_values = [r['anomaly_reason'] != '[]' or bool(r['ml_anomaly_reason']) for r in result_reasons]
        update_rows = list(zip(status_values, repeat(meeting_name), timestamps))
        fix_stmt = self.session.prepare(
            f"UPDATE {table} "
            f"SET anomaly=? "
            f"WHERE meeting_name=? AND datetime=?;"
        )
        execute_concurrent_with_args(self.session, fix_stmt, update_rows)


def build_dao(config: Config):
    auth_provider = PlainTextAuthProvider(username=config.cassandra_user, password=config.cassandra_passwd)
    cassandra = Cluster([config.cassandra_host], port=config.cassandra_port, auth_provider=auth_provider)
    session = cassandra.connect(config.keyspace)
    session.row_factory = dict_factory

    return CassandraDAO(session)
