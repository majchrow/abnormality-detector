import asyncio
import json
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from datetime import datetime as dt

from .db import CassandraDAO, build_dao
from ..workers import main, report
from ...config import Config


class Worker:

    def __init__(self, job_consumer, producer, dao: CassandraDAO):
        self.dao = dao
        self.job_consumer = job_consumer
        self.kafka_producer = producer

        self.loop = None

    async def start(self):
        report('started')
        self.loop = asyncio.get_running_loop()
        await self.process_jobs()

    async def process_jobs(self):
        async for msg in self.job_consumer:
            msg_dict = json.loads(msg.value)

            meeting_name = msg_dict['meeting_name']
            start = dt.strptime(msg_dict['start'], '%Y-%m-%d %H:%M:%S.%fZ')
            end = dt.strptime(msg_dict['end'], '%Y-%m-%d %H:%M:%S.%fZ')
            report(f'job received: run model on {meeting_name} from {start} to {end}')

            # TODO: we block here...
            threshold, ci_model, roster_model = self.dao.load_models(meeting_name)
            ci_batch, roster_batch = self.dao.load_data(meeting_name, start, end)
            ci_predictions = ci_model.predict(ci_batch)
            roster_predictions = roster_model.predict(roster_batch)

            report("CI batch")
            report(str(ci_batch.shape))
            report("ROSTER batch")
            report(str(roster_batch.shape))
            report("CI predictions")
            report(str(ci_predictions.shape))
            report("ROSTER predictions")
            report(str(roster_predictions.shape))

            def anomaly_filter(df):
                return filter_anomalies(meeting_name, threshold, df)

            ci_results, roster_results = map(anomaly_filter, [ci_predictions, roster_predictions])
            report(f'{len(ci_results) + len(roster_results)} anomalies found')

            self.dao.save_anomalies(ci_results, roster_results)
            self.dao.complete_inference_job(meeting_name, end)

            report(f'job finished: run model on {meeting_name} from {start} to {end}')
            msg = {'meeting_name': meeting_name, 'status': 'success', 'event': 'Inference job finished'}
            await self.kafka_producer.send_and_wait(topic='anomalies-job-status', value=json.dumps(msg).encode())


def filter_anomalies(meeting, threshold, scores_df):
    anomalies = []
    cnt = 0

    for ts, p in scores_df.iterrows():
        if p[0] > threshold:
            cnt += 1
            anomalies.append((threshold, str(p[0]), meeting, ts))
    report(f'Detected {cnt} anomalies')
    return anomalies


async def setup(config: Config):
    producer = AIOKafkaProducer(bootstrap_servers=config.kafka_bootstrap_server)
    await producer.start()

    job_consumer = AIOKafkaConsumer('monitoring-anomalies-jobs', bootstrap_servers=config.kafka_bootstrap_server,
                                    group_id='monitoring-workers')
    await job_consumer.start()

    dao = build_dao(config)
    return Worker(job_consumer, producer, dao)


async def teardown(worker: Worker):
    await worker.kafka_producer.stop()
    await worker.job_consumer.stop()


if __name__ == '__main__':
    main(setup, teardown)
