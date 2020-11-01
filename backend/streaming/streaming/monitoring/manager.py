import asyncio
import json
import logging
import os
from asyncio import Queue
from collections import defaultdict

from .protocol import AsyncStreams

worker_dir = os.path.dirname(os.path.realpath(__file__))


class Manager:
    def __init__(self):
        self.threshold_notifications_q = defaultdict(Queue)
        self.threshold_manager = ThresholdManager(self.threshold_notifications_q)

    async def start(self):
        await self.threshold_manager.start()

    async def dispatch(self, conf_id: str, request: dict):
        # TODO:
        if request['type'] == 'threshold':
            await self.threshold_manager.submit(conf_id, request['criteria'])

    async def shutdown(self):
        await self.threshold_manager.shutdown()


class ThresholdManager:
    def __init__(self, notification_queues):
        self.worker = None
        self.listener = None
        self.running = False
        self.notification_q = notification_queues

    async def start(self):
        self.worker = await asyncio.create_subprocess_exec(
            'python3',
            f'{os.path.join(worker_dir, "thresholds.py")}',
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        self.running = True
        self.listener = asyncio.create_task(self.listen())

    async def listen(self):
        while self.running:
            line = await AsyncStreams.read_str(self.worker.stdout)
            logging.info('bob:' + line)
            if not line:
                logging.warning('Worker process shutdown!')  # TODO: handle possible errors
                break

            payload = json.loads(line)
            conf_id, response = payload['conf_id'], payload['response']
            await self.notification_q[conf_id].put(response)

    async def submit(self, conf_id: str, criteria: dict):
        payload = {'conf_id': conf_id, 'criteria': criteria}
        await AsyncStreams.send_dict(payload, self.worker.stdin)

    async def shutdown(self):
        self.running = False
        await AsyncStreams.send_str('POISON', self.worker.stdin)
        await self.listener.cancel()
