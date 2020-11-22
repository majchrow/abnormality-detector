import asyncio
import json
import logging


class ThresholdManager:
    def __init__(self, num_workers):
        self.num_workers = num_workers
        self.workers = []
        self.kafka_producer = None

    def init(self, kafka_producer):
        self.kafka_producer = kafka_producer

    async def run(self):

        for i in range(self.num_workers):
            worker = ChildProcess(f'worker-{i}')
            self.workers.append(worker)
        await asyncio.gather(*[w.run() for w in self.workers], return_exceptions=True)

    async def schedule(self, meeting_name, criteria):
        payload = json.dumps({
            'type': 'update',
            'meeting_name': meeting_name,
            'criteria': criteria
        }).encode()
        await self.kafka_producer.send_and_wait(topic='monitoring-config', value=payload)

    async def unschedule(self, meeting_name):
        payload = json.dumps({
            'type': 'delete',
            'meeting_name': meeting_name
        }).encode()
        await self.kafka_producer.send_and_wait(topic='monitoring-config', value=payload)

    async def shutdown(self):
        await asyncio.gather(*[w.stop() for w in self.workers])


class ChildProcess:
    def __init__(self, uid: str):
        self.uid = uid
        self.worker = None
        self.task = None

    async def run(self):
        self.worker = await asyncio.create_subprocess_exec(
            'python3', '-m', 'streaming.monitoring.thresholds.monitor',
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        await asyncio.gather(*[self._listen(self.worker.stdout), self._listen(self.worker.stderr)])
        # TODO: some life check and restart! (worker.is_alive()?)

    async def stop(self):
        self.worker.kill()
        await self.worker.wait()

    async def _listen(self, stream):
        while True:
            line = (await stream.readline()).decode()
            if not line:
                await asyncio.sleep(1)
            else:
                logging.info(f'{self.uid}: {line}')
