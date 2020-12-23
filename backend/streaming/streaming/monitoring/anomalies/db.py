import pandas as pd
from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster, dict_factory
from cassandra.concurrent import execute_concurrent_with_args
from cassandra.query import ValueSequence
from contextlib import contextmanager
from datetime import datetime
from itertools import repeat
from uuid import uuid4

from .exceptions import MissingDataError
from .model import Model
from ..workers import report
from ...config import Config


class CassandraDAO:
    def __init__(self, session):
        self.session = session

    ##########
    # training
    ##########
    def load_training_job(self, job_id):
        result = self.session.execute(
            f'SELECT * FROM training_jobs '
            f'WHERE job_id=%s;',
            (job_id,)
        ).all()
        return result[0] if result else None

    def load_calls_data(self, meeting_name, call_starts):
        if not call_starts:
            raise MissingDataError

        calls = self.session.execute(
            f'SELECT start_datetime as start, last_update as end '
            f'FROM calls '
            f'WHERE meeting_name=%s AND start_datetime IN %s;',
            (meeting_name, ValueSequence(call_starts))
        ).all()

        calls_dfs = [self.load_data(meeting_name, call['start'], call['end']) for call in calls]
        if not calls_dfs:
            raise MissingDataError

        ci_dfs, roster_dfs = zip(*calls_dfs)
        return pd.concat(ci_dfs), pd.concat(roster_dfs)

    def save_models(self, ci_model, roster_model, calls, threshold):
        self.session.execute(
            f'INSERT INTO models(meeting_name, training_call_starts, threshold, call_info_model, roster_model) '
            f'VALUES (%s, %s, %s, %s, %s);',
            (ci_model.meeting_name, calls, threshold, ci_model.serialize(), roster_model.serialize())
        )

    def complete_training_job(self, job_id, status='completed'):
        self.session.execute(
            f"UPDATE training_jobs "
            f"SET status=%s "
            f"WHERE job_id=%s;",
            (status, job_id,)
        )

    ###########
    # inference
    ###########
    def load_models(self, meeting_name):
        result = self.session.execute(
            f'SELECT threshold, call_info_model, roster_model FROM models '
            f'WHERE meeting_name=%s;',
        (meeting_name,)).all()
        if not result:
            raise MissingModelError

        ci_model = Model(meeting_name)
        roster_model = Model(meeting_name)
        ci_model.deserialize(result[0]['call_info_model'])
        roster_model.deserialize(result[0]['roster_model'])
        return float(result[0]['threshold']), ci_model, roster_model

    def load_data(self, meeting_name, start, end):
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

        def select(row_dict):
            return {k: v for k, v in row_dict.items() if k in Model.get_columns()}

        ci_sel, roster_sel = list(map(select, ci_result)), list(map(select, roster_result))
        ci_df = pd.DataFrame.from_records(ci_sel, index=['datetime'])
        roster_df = pd.DataFrame.from_records(roster_sel, index=['datetime'])
        return ci_df, roster_df

    def save_anomalies(self, ci_results, roster_results):
        with self.try_lock('anomaly-status-update') as locked:
            if not locked:
                report('failed to obtain anomaly-status-update lock')
                return
            report('obtained anomaly-status-update lock')

            if ci_results:
                ci_stmt = self.session.prepare(
                    f"UPDATE call_info_update "
                    f"SET anomaly=true, threshold=?, ml_anomaly_reason=? "
                    f"WHERE meeting_name=? AND datetime=?;"
                )
                execute_concurrent_with_args(self.session, ci_stmt, ci_results)
            if roster_results:
                roster_stmt = self.session.prepare(
                    f"UPDATE roster_update "
                    f"SET anomaly=true, threshold=?, ml_anomaly_reason=? "
                    f"WHERE meeting_name=? AND datetime=?;"
                )
                execute_concurrent_with_args(self.session, roster_stmt, roster_results)
        report('released anomaly-status-update lock')

    def save_anomaly_status(self, ci_results, roster_results):
        with self.try_lock('anomaly-status-update') as locked:
            if not locked:
                report('failed to obtain anomaly-status-update lock')
                return
            report('obtained anomaly-status-update lock')

            if ci_results:
                meeting_name = ci_results[0][2]
                ci_stmt = self.session.prepare(
                    f"UPDATE call_info_update "
                    f"SET threshold=?, ml_anomaly_reason=? "
                    f"WHERE meeting_name=? AND datetime=?;"
                )
                execute_concurrent_with_args(self.session, ci_stmt, ci_results)
                self.fix_anomaly_status('call_info_update', meeting_name, [r[3].to_pydatetime() for r in ci_results])
            if roster_results:
                meeting_name = roster_results[0][2]
                roster_stmt = self.session.prepare(
                    f"UPDATE roster_update "
                    f"SET threshold=?, ml_anomaly_reason=? "
                    f"WHERE meeting_name=? AND datetime=?;"
                )
                execute_concurrent_with_args(self.session, roster_stmt, roster_results)
                self.fix_anomaly_status('roster_update', meeting_name, [r[3].to_pydatetime() for r in roster_results])
        report('released anomaly-status-update lock')

    def fix_anomaly_status(self, table, meeting_name, timestamps):
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

    def complete_inference_job(self, meeting_name, end_datetime):
        self.session.execute(
            f"UPDATE inference_jobs "
            f"SET status='completed' "
            f"WHERE meeting_name=%s AND end_datetime=%s;",
            (meeting_name, end_datetime)
        )

    @contextmanager
    def try_lock(self, resource):
        try:
            # lock using Cassandra's lightweight transactions
            now = datetime.now()
            uid = str(uuid4())
            result = self.session.execute(
                f'UPDATE locks SET lock_id=%s, last_locked=%s '
                f'WHERE resource_name=%s '
                f'IF lock_id=null;',
                (uid, now, resource)
            ).all()
            yield result[0]['[applied]']
        finally:
            self.session.execute(
                'UPDATE locks SET lock_id=null '
                'WHERE resource_name=%s;',
                (resource,)
            )


def build_dao(config: Config):
    auth_provider = PlainTextAuthProvider(username=config.cassandra_user, password=config.cassandra_passwd)
    cassandra = Cluster([config.cassandra_host], port=config.cassandra_port, auth_provider=auth_provider)
    session = cassandra.connect(config.keyspace)
    session.row_factory = dict_factory

    return CassandraDAO(session)
