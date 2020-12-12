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
        self.meeting_models = {}

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
            ci_model, roster_model = self.dao.load_models(meeting_name)
            ci_batch, roster_batch = self.dao.load_data(meeting_name, start, end)
            if not ci_batch.empty:
                ci_results = ci_model.predict(ci_batch)
            else:
                ci_results = []
            if not roster_batch.empty:
                roster_results = roster_model.predict(roster_batch)
            else:
                roster_results = []
            self.dao.save_anomalies(meeting_name, ci_results, roster_results)
            # TODO: complete inference
            report(f'job finished: run model on {meeting_name} from {start} to {end}')


async def setup(config: Config):
    producer = AIOKafkaProducer(bootstrap_servers=config.kafka_bootstrap_server)
    await producer.start()

    job_consumer = AIOKafkaConsumer('monitoring-anomalies-jobs', bootstrap_servers=config.kafka_bootstrap_server)
    await job_consumer.start()

    dao = build_dao(config)

    return Worker(job_consumer, producer, dao)


async def teardown(worker: Worker):
    await worker.kafka_producer.stop()
    await worker.job_consumer.stop()


if __name__ == '__main__':
    main(setup, teardown)
