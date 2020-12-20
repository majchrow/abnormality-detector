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


def main(serialized_job):
    config = Config()
    producer = KafkaProducer(bootstrap_servers=[config.kafka_bootstrap_server])
    dao = build_dao(config)

    job = json.loads(serialized_job)
    meeting_name = job['meeting_name']
    criteria = validate(job['criteria'])
    start = dt.strptime(job['start'], '%Y-%m-%d %H:%M:%S.%fZ')
    end = dt.strptime(job['end'], '%Y-%m-%d %H:%M:%S.%fZ')

    call_records, ci_records, roster_records = dao.load_data(meeting_name, start, end)
    call_records = list(zip(call_records, repeat(MsgType.CALLS)))
    ci_records = list(zip(ci_records, repeat(MsgType.CALL_INFO)))
    roster_records = list(zip(roster_records, repeat(MsgType.ROSTER)))

    report(f'loaded training data: {len(call_records)} from calls, {len(ci_records)} from call_info, {len(roster_records)} from roster')

    results = {MsgType.CALLS: [], MsgType.CALL_INFO: [], MsgType.ROSTER: []}
    cnt = 0

    for rec, tpe in call_records + ci_records + roster_records:
        anomalies = check(rec, tpe, criteria)
        reason = json.dumps([a.dict() for a in anomalies])
        timestamp = rec['start_datetime'] if tpe == MsgType.CALLS else rec['datetime']
        results[tpe].append((bool(anomalies), reason, meeting_name, timestamp))
        if anomalies:
            cnt += 1
    report(f'Detected {cnt} anomalies')

    dao.save_anomaly_status(results[MsgType.CALLS], results[MsgType.CALL_INFO], results[MsgType.ROSTER])
    report(f'inference job finished: run thresholds on {meeting_name} from {start} to {end}')

    msg = {'meeting_name': job['meeting_name'], 'status': 'success', 'event': 'Monitoring job finished'}
    push_to_kafka(msg, producer)


if __name__ == '__main__':
    main(sys.argv[1])
