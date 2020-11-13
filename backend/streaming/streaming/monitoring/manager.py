import asyncio
import json
import logging
from aiohttp import web
from aiokafka import AIOKafkaConsumer
from asyncio import Queue
from collections import defaultdict
from typing import Tuple

from .monitor import Monitor


# Workflow:
#  - request for some call comes in to Manager
#  - if no task for this call yet - a task is launched:
#    - it registers with Kafka to receive messages from this call
#    - for each message it takes the criteria defined, evaluates them, pushes result to output queue
#  - if task exists already - criteria are updated (God bless single threaded approach)
#  - if we want to unschedule some monitoring - just kill the task & clean up, neat
#
# Note: can be scaled up easily by running multiple processes (on whatever machines), also easy
# to persist these monitoring tasks (in case of failure or user wanting to see them all)

# So responsible for:
#  - listening to Kafka
#  - managing threshold tasks end-to-end
#  - MAYBE (no idea really) will launch some long running machine learning tasks
#    - maybe a process pool of executors running predictions (...) for multiple calls (process per call seems wasteful)
#    - child processes - better not
#    - could use gunicorn for managing child processes actually - would require another service...
#    - or, instead of a separate service and self-managed process pool - a task queue like Celery (requires broker...)
class Manager:

    class UnmonitoredError(Exception):
        pass

    def __init__(self, config):
        self.kafka_manager = KafkaManager(config.kafka_bootstrap_server, config.kafka_topic_map)
        self.threshold_manager = ThresholdManager(self.kafka_manager)
        # TODO: other managers for e.g. running ML predictions, retraining model etc.

    def start(self):
        self.kafka_manager.start()

    async def schedule(self, monitoring_key: Tuple[str, str], request: dict):
        if request['type'] == 'threshold':
            self.threshold_manager.schedule(monitoring_key, request['criteria'])

    async def unschedule(self, conf_name, request):
        if request['type'] == 'threshold':
            await self.threshold_manager.unschedule(conf_name)

    async def receive(self, call_name):
        if not (task := self.threshold_manager.monitoring_tasks.get(call_name, None)):
            raise Manager.UnmonitoredError()

        while True:
            msg = await task.output_queue.get()
            if msg == 'POISON':  # TODO: factor out the magic
                break
            yield msg

    async def shutdown(self):
        await self.threshold_manager.shutdown()
        logging.info('Worker manager task shutdown finished.')


class ThresholdManager:

    def __init__(self, event_source):
        self.event_source = event_source
        self.monitoring_tasks = {}

    def schedule(self, monitoring_key: Tuple[str, str], criteria):
        if task := self.monitoring_tasks.get(monitoring_key, None):
            task.update_criteria(criteria)
        else:
            task = MonitoringTask()
            task.update_criteria(criteria)
            self.event_source.subscribe(monitoring_key, task.input_queue)
            task.start()

    async def unschedule(self, monitoring_key: Tuple[str, str]):
        if task := self.monitoring_tasks.get(monitoring_key, None):
            await task.stop()
            await task.output_queue.put('POISON')

    async def shutdown(self):
        await asyncio.gather(*[task.stop() for task in self.monitoring_tasks.values()])


class MonitoringTask:
    def __init__(self):
        self.input_queue = Queue()
        self.output_queue = Queue()
        self.checker = Monitor()

        self.task = None

    def start(self):
        self.task = asyncio.create_task(self._run())

    async def stop(self):
        self.task.cancel()
        await self.task

    async def _run(self):
        # TODO: error handling
        while True:
            msg = await self.input_queue.get()
            result = self.checker.verify(msg)
            if result:
                await self.output_queue.put(result)

    def update_criteria(self, criteria):
        self.checker.set_criteria(criteria)


class KafkaManager:

    def __init__(self, bootstrap_server, input_topic_map):
        self.bootstrap_server = bootstrap_server
        self.consumer = None
        self.task = None
        self.event_sinks = defaultdict(set)
        self.input_topics = input_topic_map

    def start(self):
        self.task = asyncio.create_task(self._run())

    async def stop(self):
        self.task.cancel()
        await self.task

    async def _run(self):
        topics = list(self.input_topics.keys())
        self.consumer = AIOKafkaConsumer(*topics, bootstrap_servers=self.bootstrap_server)

        await self.consumer.start()
        try:
            async for msg in self.consumer:
                msg_dict = json.loads(msg.value.decode())

                # TODO: this dispatch must match what's produced during preprocessing!
                topic = self.input_topics[msg.topic]
                if topic == 'callListUpdate':
                    if msg_dict['message']['updates']:
                        call_name = msg_dict['message']['updates'][0]['name']
                    else:
                        continue
                elif topic == 'callInfoUpdate':
                    call_name = msg_dict['message']['callInfo']['name']
                else:
                    call_name = msg_dict['name']

                sinks = self.event_sinks[call_name]
                for queue in sinks | self.event_sinks[('ALL', 'ALL')]:  # TODO: remove dark magic!
                    # TODO: could also launch a task so as not to block Kafka connector
                    logging.info(f'PUT: {msg_dict}')
                    await queue.put(msg_dict)
        finally:
            await self.consumer.stop()

    def subscribe(self, monitoring_key, queue):
        self.event_sinks[monitoring_key].add(queue)

    def unsubscribe(self, monitoring_key, queue):
        self.event_sinks[monitoring_key].discard(queue)
        if not self.event_sinks[monitoring_key]:
            del self.event_sinks[monitoring_key]


async def start_all(app: web.Application):
    app['monitoring'].start()


async def cancel_all(app: web.Application):
    await app['monitoring'].shutdown()


def setup_monitoring(app: web.Application, config):
    manager = Manager(config)
    app['monitoring'] = manager
    app.on_startup.append(start_all)
    app.on_cleanup.append(cancel_all)
