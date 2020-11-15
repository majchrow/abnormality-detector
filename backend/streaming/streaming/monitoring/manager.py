import asyncio
import json
import logging
from aiohttp import web
from aiokafka import AIOKafkaConsumer
from typing import Optional

from ..exceptions import UnmonitoredError
from .thresholds import ThresholdManager


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
class Manager:

    TAG = 'Manager'

    def __init__(self, config):
        self.kafka_manager = KafkaManager(config.kafka_bootstrap_server, config.kafka_topic_map)
        self.threshold_manager = ThresholdManager(self.kafka_manager)
        # TODO: other managers for e.g. running ML predictions, retraining model etc.

    def start(self):
        self.kafka_manager.start()

    async def schedule(self, conf_name: Optional[str], request: dict):
        if request['type'] == 'threshold':
            self.threshold_manager.schedule(conf_name, request['criteria'])

    async def get_criteria(self, conf_name: Optional[str], monitoring_type: str):
        if monitoring_type == 'threshold':
            return self.threshold_manager.get_criteria(conf_name)

    async def get_all_criteria(self):
        criteria = []
        for manager in [self.threshold_manager]:
            criteria.extend(manager.get_all_criteria())
        return criteria

    async def unschedule(self, conf_name: Optional[str], monitoring_type: str):
        if monitoring_type == 'threshold':
            await self.threshold_manager.unschedule(conf_name)

    def receiver(self, call_name):
        if not (task := self.threshold_manager.monitoring_tasks.get(call_name, None)):
            raise UnmonitoredError()

        async def _receiver():
            while True:
                msg = await task.output_queue.get()
                if msg == ThresholdManager.STREAM_FINISHED:
                    break
                yield msg
        return _receiver

    async def shutdown(self):
        await self.threshold_manager.shutdown()
        logging.info(f'{self.TAG}: shutdown finished')


class KafkaManager:

    TAG = 'KafkaManager'

    class SubscriptionKey:
        ALL = 'ALL CONFERENCES'

        def __init__(self, conference_name: Optional[str]):
            if conference_name is None:
                self.value = self.ALL
            else:
                self.value = ('SINGLE', conference_name)

        def __eq__(self, other):
            if isinstance(other, KafkaManager.SubscriptionKey):
                return self.value == other.value
            elif other == self.value == self.ALL:
                return True

        def __hash__(self):
            return hash(self.value)

        def __str__(self):
            if self.value == self.ALL:
                return self.value
            else:
                return self.value[1]

    def __init__(self, bootstrap_server, input_topic_map):
        self.bootstrap_server = bootstrap_server
        self.task = None
        self.event_sinks = {}
        self.input_topics = input_topic_map  # preprocessed output topic -> CMS event type

    def start(self):
        self.task = asyncio.create_task(self._run())

    async def stop(self):
        self.task.cancel()
        await self.task

    @property
    def all_events_sink(self):
        if sink := self.event_sinks.get(self.SubscriptionKey.ALL, None):
            return next(iter(sink))
        return None

    async def _run(self):
        topics = list(self.input_topics.keys())
        consumer = AIOKafkaConsumer(*topics, bootstrap_servers=self.bootstrap_server)

        await consumer.start()
        try:
            async for msg in consumer:
                msg_dict = json.loads(msg.value.decode())

                topic = self.input_topics[msg.topic]
                key = self.SubscriptionKey(msg_dict['name'])

                sinks = self.event_sinks.get(key, set())
                if self.all_events_sink:
                    sinks = sinks.union({self.all_events_sink})

                if not sinks:
                    continue

                logging.info(f'push {msg_dict} from topic {topic} to {len(sinks)} monitors')
                for queue in sinks:
                    queue.put_nowait((topic, msg_dict))
        finally:
            await consumer.stop()

    def subscribe(self, conf_name: Optional[str], queue):
        key = KafkaManager.SubscriptionKey(conf_name)
        logging.info(f'{self.TAG}: registered subscriber for {key}')

        if (sinks := self.event_sinks.get(key, None)) is None:
            sinks = set()
            self.event_sinks[key] = sinks
        sinks.add(queue)

    def unsubscribe(self, conf_name: Optional[str], queue):
        key = KafkaManager.SubscriptionKey(conf_name)
        if not (sinks := self.event_sinks.get(key, None)):
            logging.warning(f'{self.TAG}: "unsubscribe" attempt for {key} - conference unmonitored!')
        else:
            try:
                sinks.remove(queue)
                logging.info(f'{self.TAG}: unregistered subscriber for {key}, size {len(sinks)}')
                if not sinks:
                    del self.event_sinks[key]
            except KeyError:
                logging.warning(f'{self.TAG}: "unsubscribe" attempt for {key} - not a subscriber!')


async def start_all(app: web.Application):
    app['monitoring'].start()


async def cancel_all(app: web.Application):
    await app['monitoring'].shutdown()


def setup_monitoring(app: web.Application, config):
    manager = Manager(config)
    app['monitoring'] = manager
    app.on_startup.append(start_all)
    app.on_cleanup.append(cancel_all)
