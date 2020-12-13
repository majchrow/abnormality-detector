import asyncio
import json
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster, dict_factory
from dateutil.parser import isoparse

from . import STREAM_FINISHED
from .criteria import check, validate, MsgType
from ..workers import main, report
from ...config import Config


class Worker:

    def __init__(self, config, cassandra_session,data_consumer, config_consumer, producer):
        self.calls_table = config.calls_table
        self.call_info_table = config.call_info_table
        self.roster_table = config.roster_table
        self.meetings_table = config.meetings_table
        self.session = cassandra_session
        self.session.row_factory = dict_factory
        self.data_consumer = data_consumer
        self.config_consumer = config_consumer
        self.kafka_producer = producer
        self.monitoring_criteria = {}

        self.loop = None

    async def start(self):
        report('started')
        try:
            await self.bootstrap()
        except Exception as e:
            report(f'bootstrap failed with {e}')
            return

        self.loop = asyncio.get_running_loop()
        await asyncio.gather(self.process_config(), self.process_data())

    async def bootstrap(self):
        meetings = await self.get_monitored_meetings()
        self.monitoring_criteria = {m['name']: validate(m['criteria']) for m in meetings}
        report(f'bootstrapped from {len(meetings)} meetings')

    async def process_config(self):
        async for msg in self.config_consumer:
            msg_dict = json.loads(msg.value)

            meeting_name = msg_dict['meeting_name']
            config_type = msg_dict['type']
            report(f'received configuration {config_type} for {meeting_name}')

            if config_type == 'update':
                criteria = validate(msg_dict['criteria'])
                self.monitoring_criteria[meeting_name] = criteria
            elif config_type == 'delete':
                if self.monitoring_criteria.pop(meeting_name, None):
                    payload = json.dumps({'meeting': meeting_name, 'anomalies': STREAM_FINISHED})
                    await self.kafka_producer.send_and_wait('monitoring-anomalies', payload.encode())
            else:
                # TODO: log unknown?
                pass

    async def process_data(self):
        async for msg in self.data_consumer:
            msg_dict = json.loads(msg.value)
            meeting_name = msg_dict['meeting_name']

            if not (criteria := self.monitoring_criteria.get(meeting_name, None)):
                continue

            msg_type = MsgType(msg.topic.split('_', 1)[1])
            anomalies = check(msg_dict, msg_type, criteria)
            if anomalies:
                payload = json.dumps({'meeting': meeting_name, 'anomalies': [a.dict() for a in anomalies]})
                # TODO: create task?
                await self.kafka_producer.send("monitoring-results-anomalies", payload.encode())
                self.set_anomaly(msg_dict, msg.topic, anomalies)
                report(f'detected {len(anomalies)} anomalies')

    def get_monitored_meetings(self):
        result = self.session.execute_async(
            f'SELECT meeting_name as name, criteria FROM {self.meetings_table} '
            f'WHERE monitored=true ALLOW FILTERING;'
        )

        loop = asyncio.get_running_loop()
        future = loop.create_future()

        def on_success(meetings):
            for m in meetings:
                m['criteria'] = json.loads(m['criteria'])
            future.set_result(meetings)

        def on_error(e):
            future.set_exception(e)

        result.add_callbacks(on_success, on_error)
        return future

    def set_anomaly(self, msg_dict, topic, anomalies):
        reason = json.dumps([a.dict() for a in anomalies])
        meeting_name = msg_dict['meeting_name']

        if topic == 'preprocessed_callListUpdate':
            start_datetime, datetime = map(isoparse, [msg_dict['start_datetime'], msg_dict['last_update']])
            future = self.session.execute_async(
                f'UPDATE {self.calls_table} '
                f'SET anomaly=true, anomaly_reason=%s '
                f'WHERE meeting_name=%s AND start_datetime=%s;',
            (reason, meeting_name, start_datetime))
        else:
            if topic == 'preprocessed_callInfoUpdate':
                table = self.call_info_table
            else:
                table = self.roster_table

            datetime = isoparse(msg_dict['datetime'])
            future = self.session.execute_async(
                f'UPDATE {table} '
                f'SET anomaly=true, anomaly_reason=%s '
                f'WHERE meeting_name=%s AND datetime=%s;',
            (reason, meeting_name, datetime))

        future.add_callbacks(
            lambda _: report(f'set anomaly status for call {meeting_name} at {datetime}'),
            lambda e: report(f'"set anomaly" for {meeting_name} at {datetime} failed with {e}')
        )


async def setup(config: Config):
    producer = AIOKafkaProducer(bootstrap_servers=config.kafka_bootstrap_server)
    await producer.start()

    data_consumer = AIOKafkaConsumer(
        'preprocessed_callListUpdate', 'preprocessed_callInfoUpdate', 'preprocessed_rosterUpdate',
        bootstrap_servers=config.kafka_bootstrap_server, group_id='monitoring-workers'
    )

    config_consumer = AIOKafkaConsumer('monitoring-thresholds-config', bootstrap_servers=config.kafka_bootstrap_server)

    await data_consumer.start()
    await config_consumer.start()

    auth_provider = PlainTextAuthProvider(username=config.cassandra_user, password=config.cassandra_passwd)
    cassandra = Cluster([config.cassandra_host], port=config.cassandra_port, auth_provider=auth_provider)
    session = cassandra.connect(config.keyspace)

    return Worker(
        config, session, data_consumer, config_consumer, producer
    )


async def teardown(worker: Worker):
    await worker.kafka_producer.stop()
    await worker.data_consumer.stop()
    await worker.config_consumer.stop()


if __name__ == '__main__':
    main(setup, teardown)
