import asyncio
import logging
from asyncio import Queue

from ...exceptions import UnmonitoredError
from .criteria import check, validate, MsgType


class ThresholdManager:

    TAG = 'ThresholdManager'
    STREAM_FINISHED = 'END STREAM'

    def __init__(self, event_source, dao):
        self.event_source = event_source
        self.dao = dao
        self.monitoring_tasks = {}

    def schedule(self, conf_name: str, criteria: dict):
        if task := self.monitoring_tasks.get(conf_name, None):
            task.update_criteria(criteria)
        else:
            task = MonitoringTask(conf_name, self.dao)
            task.update_criteria(criteria)
            self.monitoring_tasks[conf_name] = task
            self.event_source.monitoring_subscribe(conf_name, task.input_queue)
            task.start()
        logging.info(f'{self.TAG}: scheduled monitoring for {conf_name if conf_name else "ALL"}')

    async def unschedule(self, conf_name: str):
        if task := self.monitoring_tasks.get(conf_name, None):
            self.event_source.monitoring_unsubscribe(conf_name, task.input_queue)
            del self.monitoring_tasks[conf_name]
            await task.stop()
            logging.info(f'{self.TAG}: unscheduled monitoring for {conf_name if conf_name else "ALL"}')
        else:
            logging.warning(f'{self.TAG}: "unschedule" attempt for unmonitored {conf_name if conf_name else "ALL"}')
            raise UnmonitoredError()

    def get_all_monitored(self):
        return list(self.monitoring_tasks.keys())

    def is_monitored(self, conf_name: str):
        return conf_name in self.monitoring_tasks

    async def shutdown(self):
        await asyncio.gather(*[task.stop() for task in self.monitoring_tasks.values()])
        logging.info(f'{self.TAG}: stopped')


class MonitoringTask:

    TAG = 'MonitoringTask'

    def __init__(self, conf_name, dao):
        self.conf_name = conf_name
        self.dao = dao
        self.input_queue = Queue()
        self.output_queues = set()
        self.criteria = None
        self.task = None

    def start(self):
        self.task = asyncio.create_task(self._run())

    async def stop(self):
        self.task.cancel()
        await self.task
        for queue in self.output_queues:
            await queue.put(ThresholdManager.STREAM_FINISHED)

    def subscribe(self, queue):
        self.output_queues.add(queue)
        logging.info(f'{self.TAG}: registered monitoring task subscriber for {self.conf_name}')

    def unsubscribe(self, queue):
        if queue in self.output_queues:
            self.output_queues.remove(queue)
            logging.info(f'{self.TAG}: unregistered subscriber for monitoring task of {self.conf_name} ')
        else:
            logging.info(f'{self.TAG}: "unsubscribe monitoring for {self.conf_name}" attempt - subscriber not found')

    async def _run(self):
        # TODO: better error handling
        try:
            while True:
                topic, msg = await self.input_queue.get()
                msg_type = MsgType(topic)
                anomalies = check(msg, msg_type, self.criteria)

                if anomalies:
                    logging.info(f'{self.TAG}: detected {len(anomalies)} anomalies for {self.conf_name}')
                    for queue in self.output_queues:
                        queue.put_nowait(anomalies)

                    self.dao.add_anomaly(msg['name'], msg['datetime'], anomalies)
        except asyncio.CancelledError:
            pass

    def update_criteria(self, criteria):
        self.criteria = validate(criteria)  # throws ValidatedError
