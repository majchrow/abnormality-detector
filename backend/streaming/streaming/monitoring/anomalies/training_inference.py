import json
import sys
from datetime import datetime as dt
from kafka import KafkaProducer
from kafka.errors import KafkaError

from .db import build_dao
from .exceptions import MissingDataError
from .model import Model
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
    
    try:
        ci_df, roster_df = dao.load_calls_data(meeting_name, job['training_call_starts'])
        report(f'loaded training data: call-info {ci_df.shape}, roster {roster_df.shape}')
    except MissingDataError:
        report('job invalid - no data')
        report('all done')

        msg = {'meeting_name': meeting_name, 'status': 'failed - no training data'}
        push_to_kafka(msg, producer)
        return

    ci_model = Model(meeting_name)
    roster_model = Model(meeting_name)

    # Training
    ci_model.train(ci_df)
    report('call info training finished')

    roster_model.train(roster_df)
    report('roster training finished')

    # Inference
    start = dt.strptime(job['start'], '%Y-%m-%d %H:%M:%S.%fZ')
    end = dt.strptime(job['end'], '%Y-%m-%d %H:%M:%S.%fZ')
    threshold = float(job['threshold'])

    ci_batch, roster_batch = dao.load_data(meeting_name, start, end)
    ci_predictions = ci_model.predict(ci_batch)
    roster_predictions = roster_model.predict(roster_batch)

    def anomaly_filter(df):
        return map_anomaly_status(meeting_name, threshold, df)

    ci_results, roster_results = map(anomaly_filter, [ci_predictions, roster_predictions])
    dao.save_anomaly_status(ci_results, roster_results)

    report(f'inference job finished: run model on {meeting_name} from {start} to {end}')

    msg = {'meeting_name': job['meeting_name'], 'status': 'success'}
    push_to_kafka(msg, producer)


def map_anomaly_status(meeting, threshold, scores_df):
    anomalies = []
    for ts, p in scores_df.iterrows():
        anomalies.append((p[1] > threshold, p[1], meeting, ts))
    return anomalies


if __name__ == '__main__':
    main(sys.argv[1])
