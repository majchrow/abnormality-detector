import asyncio
import json
import sys
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, ConsumerRebalanceListener
from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster

from . import STREAM_FINISHED
from .criteria import check, validate, MsgType


def report(stuff: str):
    sys.stdout.write(stuff + '\n')
    sys.stdout.flush()


# TODO:
#  for the _cleanup to work properly with rebalance we'd have to set key=call_name
#  on callInfoUpdate and rosterUpdate messages
class Worker:

    def __init__(
        self, call_info_table, roster_table, cassandra_session,
        data_consumer, config_consumer, producer
    ):
        self.call_info_table = call_info_table
        self.roster_table = roster_table
        self.session = cassandra_session
        self.data_consumer = data_consumer
        self.config_consumer = config_consumer
        self.kafka_producer = producer
        self.monitoring_criteria = {}
        self.monitoring_last = {}

        self.rebalance_in_progress = False
        self.loop = None

    async def start(self):
        self.loop = asyncio.get_event_loop()
        await asyncio.gather(self._cleanup(), self.process_config(), self.process_data())

    # necessary due to Kafka consumer group re-balancing
    async def _cleanup(self):
        while True:
            await asyncio.sleep(60)
            now = self.loop.time()

            stale = []
            for meeting_name, last_update in self.monitoring_last.items():
                if now - last_update > 60:
                    stale.append(meeting_name)

            for name in stale:
                del self.monitoring_criteria[name]
                del self.monitoring_last[name]
            if stale:
                report(f'cleaned up stale monitoring tasks for {stale}')

    async def process_config(self):
        async for msg in self.config_consumer:
            msg_dict = json.loads(msg.value)
            config_type = msg_dict['config_type']

            report(f'received configuration: {msg_dict}')

            if config_type == 'update':
                meeting_name, criteria = msg.key.decode(), validate(msg_dict['criteria'])
                self.monitoring_criteria[meeting_name] = criteria
                self.monitoring_last[meeting_name] = self.loop.time()
            elif config_type == 'delete':
                meeting_name = msg.key.decode()
                if self.monitoring_criteria.pop(meeting_name, None):
                    del self.monitoring_last[meeting_name]
                    payload = json.dumps({'meeting': meeting_name, 'anomalies': STREAM_FINISHED})
                    await self.kafka_producer.send_and_wait("monitoring-anomalies", payload.encode())
            else:
                # TODO: log unknown?
                pass

    async def process_data(self):
        async for msg in self.data_consumer:
            msg_dict = json.loads(msg.value)
            meeting_name = msg_dict['name']

            if not (criteria := self.monitoring_criteria.get(meeting_name, None)):
                continue

            self.monitoring_last[meeting_name] = self.loop.time()

            msg_type = MsgType(msg.topic[len('preprocessed_'):])
            anomalies = check(msg_dict, msg_type, criteria)

            if anomalies:
                payload = json.dumps({'meeting': meeting_name, 'anomalies': [a.dict() for a in anomalies]})
                # TODO: create task?
                await self.kafka_producer.send("monitoring-anomalies", payload.encode())
                self.set_anomaly(msg_dict['name'], msg_dict['datetime'], msg.topic, anomalies)

    def set_anomaly(self, meeting_name, datetime, topic, anomalies):
        if topic == 'callInfoUpdate':
            table = self.call_info_table
        else:
            table = self.roster_table

        reason = json.dumps([a.dict() for a in anomalies])
        future = self.session.execute_async(
            f'UPDATE {table} '
            f'SET anomaly=true, anomaly_reason=%s '
            f'WHERE meeting_name=%s AND datetime=%s;',
        (reason, meeting_name, datetime))

        future.add_callbacks(
            lambda _: report(f'set anomaly status for call {meeting_name} at {datetime}'),
            lambda e: report(f'"set anomaly" for {meeting_name} at {datetime} failed with {e}')
        )


async def run():
    # TODO: parameters from cmd line arguments (from parent)
    producer = AIOKafkaProducer(bootstrap_servers='kafka:29092')
    await producer.start()

    data_consumer = AIOKafkaConsumer(
        'preprocessed_callInfoUpdate', 'preprocessed_rosterUpdate', bootstrap_servers='kafka:29092'
    )

    config_consumer = AIOKafkaConsumer(
        'monitoring-config', bootstrap_servers='kafka:29092', group_id='monitoring-workers'
    )

    await data_consumer.start()
    await config_consumer.start()

    auth_provider = PlainTextAuthProvider(username='cassandra', password='cassandra')
    cassandra = Cluster(['cassandra'], port=9042, auth_provider=auth_provider)
    session = cassandra.connect('test')

    worker = Worker('call_info_update', 'roster_update', session, data_consumer, config_consumer, producer)
    try:
        await worker.start()
    finally:
        # TODO: more cleanup
        await producer.stop()
        await data_consumer.stop()
        await config_consumer.stop()


def main():
    loop = asyncio.get_event_loop()
    try:
        loop.create_task(run())
        loop.run_forever()
    finally:
        loop.close()


if __name__ == '__main__':
    main()
