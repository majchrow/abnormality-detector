import asyncio
import json
import os
from asyncio import Queue
from collections import defaultdict

from .protocol import MonitoringRequest, ThresholdCriteria, ThresholdRequest

worker_dir = os.path.dirname(os.path.realpath(__file__))


class Manager:
    def __init__(self):
        self.notify_threshold_q = defaultdict(Queue)
        self.thresholds = ThresholdManager(self.notify_threshold_q)

    async def start(self):
        await self.thresholds.start()

    # TODO: add typing!
    async def dispatch(self, conf_id: str, request: MonitoringRequest):
        if request.type == 'threshold':
            await self.thresholds.submit(conf_id, request.criteria)

    async def shutdown(self):
        await self.thresholds.shutdown()


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
            line = (await self.worker.stdout.readline()).decode()

            if not line:
                # TODO: worker process finished, handle possible errors
                break

            payload = json.loads(line)
            conf_id, response = payload['conf_id'], payload['response']
            await self.notification_q[conf_id].put(response)

    async def submit(self, conf_id: str, criteria: ThresholdCriteria):
        req = ThresholdRequest(conf_id=conf_id, criteria=criteria)
        # TODO: all stream handling to separate class?
        self.worker.stdin.write(req.bytes())
        await self.worker.stdin.drain()

    async def shutdown(self):
        self.running = False
        self.worker.stdin.write('POISON\n'.encode())
        await self.worker.stdin.drain()
        await self.worker.wait()
        await self.listener.cancel()

# TODO:
#  - module for communication protocol between processes (message classes, serialization, etc.)
#  - remember:
#    - async write: str -> (str + '\n').encode() -> sub.stdin.write() -> await sub.stdin.drain()
#    - async read: (await sub.stdin.read(str + '\n')).decode() -> str
#    - sync write: str -> sys.stdout.write(str + '\n') -> sys.stdout.flush()
#    - sync read: sys.stdin.readline() -> str
