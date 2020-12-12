import numpy as np
import pandas as pd
from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster, dict_factory
from cassandra.concurrent import execute_concurrent_with_args
from cassandra.query import ValueSequence
from itertools import chain

from .model import Model
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
        calls = self.session.execute(
            f'SELECT start_datetime as start, last_update as end '
            f'FROM calls '
            f'WHERE meeting_name=%s AND start_datetime IN %s;',
            (meeting_name, ValueSequence(call_starts))
        ).all()

        calls_dfs = [self.load_data(meeting_name, call['start'], call['end']) for call in calls]
        ci_dfs, roster_dfs = zip(*calls_dfs)
        return pd.concat(ci_dfs), pd.concat(roster_dfs)

    def save_models(self, ci_model, roster_model, calls):
        self.session.execute(
            f'INSERT INTO models(meeting_name, training_call_starts, call_info_model, roster_model) '
            f'VALUES (%s, %s, %s, %s);',
            (ci_model.meeting_name, calls, ci_model.serialize(), roster_model.serialize())
        )

    def complete_training_job(self, job_id):
        self.session.execute(
            f"UPDATE training_jobs "
            f"SET status='completed' "
            f"WHERE job_id=%s;",
            (job_id,)
        )

    ###########
    # inference
    ###########
    def load_models(self, meeting_name):
        result = self.session.execute(
            f'SELECT call_info_model, roster_model FROM models '
            f'WHERE meeting_name=%s;',
        (meeting_name,)).all()

        # TODO: handle inexistent model
        ci_model = Model(meeting_name)
        roster_model = Model(meeting_name)
        ci_model.deserialize(result[0]['call_info_model'])
        roster_model.deserialize(result[0]['roster_model'])
        return ci_model, roster_model

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
        if ci_sel:
            ci_df = pd.DataFrame.from_records(ci_sel, index='datetime')
        else:
            ci_df = pd.DataFrame([], index=['datetime'])
        if roster_sel:
            roster_df = pd.DataFrame.from_records(roster_sel, index='datetime')
        else:
            roster_df = pd.DataFrame([], index=['datetime'])
        return ci_df, roster_df

    def save_anomalies(self, meeting_name, ci_results, roster_results):
        # TODO: save explanation from the model to ml_anomaly_reason column
        if ci_results:
            ci_anomalies = [(meeting_name, timestamp) for timestamp, pred in ci_results.items() if pred]
            ci_stmt = self.session.prepare(
                f"UPDATE call_info_update "
                f"SET ml_anomaly=true "
                f"WHERE meeting_name=%s AND datetime=%s;"
            )
            execute_concurrent_with_args(self.session, ci_stmt, ci_anomalies)

        if roster_results:
            roster_anomalies = [(meeting_name, timestamp) for timestamp, pred in roster_results.items() if pred]
            roster_stmt = self.session.prepare(
                f"UPDATE roster_update "
                f"SET ml_anomaly=true "
                f"WHERE meeting_name=%s AND datetime=%s;"
            )
            execute_concurrent_with_args(self.session, roster_stmt, roster_anomalies)


def build_dao(config: Config):
    auth_provider = PlainTextAuthProvider(username=config.cassandra_user, password=config.cassandra_passwd)
    cassandra = Cluster([config.cassandra_host], port=config.cassandra_port, auth_provider=auth_provider)
    session = cassandra.connect(config.keyspace)
    session.row_factory = dict_factory

    return CassandraDAO(session)
