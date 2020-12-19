import json
import sys
from datetime import datetime as dt
from kafka import KafkaProducer
from kafka.errors import KafkaError
from itertools import repeat

from .criteria import check, validate, MsgType
from .db import build_dao
from ..workers import report
from ...config import Config


def push_to_kafka(msg, producer):
    try:
        msg = json.dumps(msg).encode()
        future = producer.send('anomalies-training', msg)
        future.get(timeout=5)
    except KafkaError:
        report(f'Failed to send {msg} to Kafka!')


# TODO:
#  - job doesn't exist
#  - no training data
#  - other failures during training?
def main(serialized_job):
    config = Config()
    producer = KafkaProducer(bootstrap_servers=[config.kafka_bootstrap_server])
    dao = build_dao(config)

    job = json.loads(serialized_job)
    meeting_name = job['meeting_name']
    criteria = validate(job['criteria'])
    start, end = job['start'], job['end']

    # TODO: calls
    ci_records, roster_records = dao.load_data(meeting_name, start, end)
    ci_records = list(zip(ci_records, repeat(MsgType.CALL_INFO)))
    roster_records = list(zip(roster_records, repeat(MsgType.ROSTER)))

    report(f'loaded training data: call-info {len(ci_records)}, roster {len(roster_records)}')

    results = {MsgType.CALL_INFO: [], MsgType.ROSTER: []}
    for rec, tpe in ci_records + roster_records:
        anomalies = check(rec, tpe, criteria)
        reason = json.dumps([a.dict() for a in anomalies])
        results[tpe].append((bool(anomalies), reason, meeting_name, rec['datetime']))

    dao.save_anomaly_status(results[MsgType.CALL_INFO], results[MsgType.ROSTER])
    report(f'inference job finished: run thresholds on {meeting_name} from {start} to {end}')

    msg = {'meeting_name': job['meeting_name'], 'status': 'success'}
    push_to_kafka(msg, producer)


def map_anomaly_status(meeting, threshold, scores_df):
    anomalies = []
    for ts, p in scores_df.iterrows():
        anomalies.append((p[1] > threshold, p[1], meeting, ts))
    return anomalies


if __name__ == '__main__':
    main(sys.argv[1])
