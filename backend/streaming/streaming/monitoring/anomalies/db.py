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

    def load_model(self, meeting_name, model_id):
        result = self.session.execute(
            f'SELECT blob FROM models '
            f'WHERE meeting_name=%s AND model_id=%s;',
        (meeting_name, model_id)).all()

        # TODO: handle incorrect model_id
        blob = result[0]['blob']
        model = Model(meeting_name, model_id)
        model.deserialize(blob)
        return model

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

        def extend(row_dict):
            return {k: row_dict.get(k, np.NaN) for k in Model.get_columns().keys()}
        ci_ext, roster_ext = list(map(extend, ci_result)), list(map(extend, roster_result))
        return pd.DataFrame(ci_ext, index=['datetime']), pd.DataFrame(roster_ext, index=['datetime'])

    def load_calls_data(self, meeting_name, call_starts):
        calls = self.session.execute(
            f'SELECT start_datetime as start, last_update as end '
            f'FROM calls '
            f'WHERE meeting_name=%s AND start_datetime IN %s;',
            (meeting_name, ValueSequence(call_starts))
        ).all()

        calls_dfs = [self.load_data(meeting_name, call['start'], call['end']) for call in calls]
        return pd.concat(chain(*calls_dfs))

    def save_model(self, model, calls):
        blob = model.serialize()
        self.session.execute(
            f'INSERT INTO models(meeting_name, model_id, training_calls, model) '
            f'VALUES (%s, %s, %s, %s);',
            (model.meeting_name, model.id, calls, blob)
        )

    def complete_training_job(self, meeting_name, submission_date):
        print(submission_date)
        self.session.execute(
            f"UPDATE training_jobs "
            f"SET status='completed' "
            f"WHERE meeting_name=%s AND submission_datetime=%s;",
            (meeting_name, submission_date)
        )

    def save_anomalies(self, meeting_name, ci_results, roster_results):
        # TODO: save explanation from the model to ml_anomaly_reason column
        ci_anomalies = [(meeting_name, timestamp) for timestamp, pred in ci_results.items() if pred]
        ci_stmt = self.session.prepare(
            f"UPDATE call_info_update "
            f"SET ml_anomaly=true "
            f"WHERE meeting_name=%s AND datetime=%s;"
        )
        execute_concurrent_with_args(self.session, ci_stmt, ci_anomalies)

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
