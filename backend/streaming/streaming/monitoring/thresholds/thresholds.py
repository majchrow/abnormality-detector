import asyncio
import logging
from asyncio import Queue
from typing import Dict, List, Literal, Optional

from ...exceptions import UnmonitoredError
from .check import check_call_info, check_roster
from .validation import validate


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
            task.update_criteria(criteria)
            self.monitoring_tasks[conf_name] = task
            self.event_source.monitoring_subscribe(conf_name, task.input_queue)
            task.start()
        logging.info(f'{self.TAG}: scheduled monitoring for {conf_name if conf_name else "ALL"}')

    async def unschedule(self, conf_name: Optional[str]):
        if task := self.monitoring_tasks.get(conf_name, None):
            self.event_source.monitoring_unsubscribe(conf_name, task.input_queue)
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
        self.criteria = None
        self.task = None

    def start(self):
        self.task = asyncio.create_task(self._run())

    async def stop(self):
        self.task.cancel()
        await self.task

    # TODO:
    #  2 things - what's returned on no anomalies + stitch together both validations
    async def _run(self):
        # TODO: better error handling
        try:
            while True:
                topic, msg = await self.input_queue.get()
                if topic == 'callInfoUpdate':
                    result = check_call_info(msg, self.criteria)
                elif topic == 'rosterUpdate':
                    result = check_roster(msg, self.criteria)
                else:
                    result = None

                if result:
                    await self.output_queue.put(result)
        except asyncio.CancelledError:
            pass

    def update_criteria(self, criteria):
        validate(criteria)  # throws ValueError
        self.criteria = criteria
