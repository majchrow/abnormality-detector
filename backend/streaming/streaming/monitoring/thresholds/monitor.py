import asyncio
import json
import sys
import traceback
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster

from . import STREAM_FINISHED
from .criteria import check, validate, MsgType
from ...config import Config


def report(stuff: str):
    sys.stdout.write(stuff + '\n')
    sys.stdout.flush()


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

        self.loop = None

    async def start(self):
        report('started')
        self.loop = asyncio.get_running_loop()
        await asyncio.gather(self.process_config(), self.process_data())

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
                await self.kafka_producer.send("monitoring-anomalies", payload.encode())
                self.set_anomaly(msg_dict['meeting_name'], msg_dict['datetime'], msg.topic, anomalies)
                report(f'detected {len(anomalies)} anomalies')

    def set_anomaly(self, meeting_name, datetime, topic, anomalies):
        if topic == 'preprocessed_callInfoUpdate':
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


async def run(config):
    producer = AIOKafkaProducer(bootstrap_servers=config.kafka_bootstrap_server)
    await producer.start()

    data_consumer = AIOKafkaConsumer(
        'preprocessed_callInfoUpdate', 'preprocessed_rosterUpdate', 
        bootstrap_servers=config.kafka_bootstrap_server, group_id='monitoring-workers'
    )

    config_consumer = AIOKafkaConsumer('monitoring-config', bootstrap_servers=config.kafka_bootstrap_server)

    await data_consumer.start()
    await config_consumer.start()
    
    auth_provider = PlainTextAuthProvider(username=config.cassandra_user, password=config.cassandra_passwd)
    cassandra = Cluster([config.cassandra_host], port=config.cassandra_port, auth_provider=auth_provider)
    session = cassandra.connect(config.keyspace)

    worker = Worker(
        config.call_info_table, config.roster_table, session, data_consumer, config_consumer, producer
    )

    try:    
        await worker.start()
    except Exception as e:
        raise e
    finally:
        await producer.stop()
        await data_consumer.stop()
        await config_consumer.stop()


def handle_exception(loop, context):
    if e := context.get('exception', None):
        msg = ''.join(traceback.format_tb(e.__traceback__))
    else:
        msg = context["message"]
    
    report('--- ERROR ---')
    report(msg)

    asyncio.create_task(shutdown(loop))


async def shutdown(loop):
    report('Shutdown initiated...')
    
    tasks = [t for t in asyncio.all_tasks() if t is not
             asyncio.current_task()]

    [task.cancel() for task in tasks]

    report(f"Cancelling {len(tasks)} outstanding tasks...")
    await asyncio.gather(*tasks, return_exceptions=True)
    report('Shutdown complete.')
    loop.stop()


def main():
    config_arg = sys.argv[1]
    config = Config(**json.loads(config_arg))

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)
    try:
        loop.create_task(run(config))
        loop.run_forever()
    finally:
        loop.close()


if __name__ == '__main__':
    main()
