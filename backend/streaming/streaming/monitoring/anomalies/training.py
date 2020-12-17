import json
import sys
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
        record_metadata = future.get(timeout=5)
    except KafkaError:
        report(f'Failed to send {msg} to Kafka!')


# TODO:
#  - job doesn't exist
#  - no training data
#  - other failures during training?
def main(job_id):
    config = Config()
    producer = KafkaProducer(bootstrap_servers=[config.kafka_bootstrap_server])

    dao = build_dao(config)
    job = dao.load_training_job(job_id)
    report(f'loaded training job {job_id}')

    try:
        ci_df, roster_df = dao.load_calls_data(job['meeting_name'], job['training_call_starts'])
        report(f'loaded training data for {job_id}: call-info {ci_df.shape}, roster {roster_df.shape}')
    except MissingDataError:
        dao.complete_training_job(job_id, 'invalid - no data')
        report('job invalid - no data')
        report('all done')

        msg = {'meeting_name': job['meeting_name'], 'status': 'failed - no training data'}
        push_to_kafka(msg, producer)
        return

    ci_model = Model(job['meeting_name'])
    roster_model = Model(job['meeting_name'])

    ci_model.train(ci_df)
    report('call info training finished')

    roster_model.train(roster_df)
    report('roster training finished')

    dao.save_models(ci_model, roster_model, job['training_call_starts'])
    report('models saved')

    dao.complete_training_job(job_id)
    report('all done')

    msg = {'meeting_name': job['meeting_name'], 'status': 'success'}
    push_to_kafka(msg, producer)


if __name__ == '__main__':
    main(sys.argv[1])
