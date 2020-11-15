import asyncio
import logging
from asyncio import Queue
from typing import Literal, Optional

from ..exceptions import UnmonitoredError


class Monitor:
    def __init__(self):
        self.criteria = None

    def set_criteria(self, criteria: dict):
        self.criteria = criteria

    def verify(self, topic: Literal['callInfoUpdate', 'rosterUpdate'], msg: dict):
        return f'Implement me! {topic} {msg} {self.criteria}'


class ThresholdManager:

    TAG = 'ThresholdManager'
    STREAM_FINISHED = 'END STREAM'

    def __init__(self, event_source):
        self.event_source = event_source
        self.monitoring_tasks = {}

    def schedule(self, conf_name: Optional[str], criteria):
        if task := self.monitoring_tasks.get(conf_name, None):
            task.update_criteria(criteria)
        else:
            task = MonitoringTask()
            self.monitoring_tasks[conf_name] = task
            task.update_criteria(criteria)
            self.event_source.subscribe(conf_name, task.input_queue)
            task.start()
        logging.info(f'{self.TAG}: scheduled monitoring for {conf_name if conf_name else "ALL"}')

    def get_criteria(self, conf_name: Optional[str]):
        logging.info(f'{self.TAG}: getting criteria for {conf_name if conf_name else "ALL"}')
        if task := self.monitoring_tasks.get(conf_name, None):
            return task.checker.criteria
        return None

    def get_all_criteria(self):
        return [
            {
                "conf_name": conf_name,
                "criteria": task.checker.criteria
            } for conf_name, task in self.monitoring_tasks.items()
        ]

    async def unschedule(self, conf_name: Optional[str]):
        if task := self.monitoring_tasks.get(conf_name, None):
            self.event_source.unsubscribe(conf_name, task.input_queue)
            del self.monitoring_tasks[conf_name]
            await task.stop()
            await task.output_queue.put(ThresholdManager.STREAM_FINISHED)
            logging.info(f'{self.TAG}: unscheduled monitoring for {conf_name if conf_name else "ALL"}')
        else:
            logging.warning(f'{self.TAG}: "unschedule" attempt for unmonitored {conf_name if conf_name else "ALL"}')
            raise UnmonitoredError()

    async def shutdown(self):
        await asyncio.gather(*[task.stop() for task in self.monitoring_tasks.values()])
        logging.info(f'{self.TAG}: stopped')


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
        # TODO: better error handling
        try:
            while True:
                topic, msg = await self.input_queue.get()
                result = self.checker.verify(topic, msg)
                if result:
                    await self.output_queue.put(result)
        except asyncio.CancelledError:
            pass

    def update_criteria(self, criteria):
        self.checker.set_criteria(criteria)
