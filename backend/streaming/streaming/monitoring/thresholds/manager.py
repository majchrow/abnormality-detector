import asyncio
import dataclasses
import json
import logging

from ...config import Config


class ThresholdManager:

    TAG = 'ThresholdManager'

    def __init__(self, config: Config):
        self.config = config
        self.num_workers = config.num_workers
        self.workers = []

        self.kafka_producer = None

    def init(self, kafka_producer):
        self.kafka_producer = kafka_producer

    async def run(self):
        for i in range(self.num_workers):
            worker = ChildProcess(f'worker-{i}', self.config)
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
        logging.info(f'{self.TAG}: shutdown')


class ChildProcess:
    def __init__(self, uid: str, config: Config):
        self.uid = uid
        self.config = config
        self.running = True
        self.worker = None
        self.task = None

    async def run(self):
        backoff = 1

        while self.running:
            logging.info(f'{self.uid} process starting...')

            await self.run_once()
            await self.worker.wait()
            logging.info(f'{self.uid} process completed')
            await asyncio.sleep(backoff)

            # Reset so that backoff doesn't stay large all the time
            if (backoff := backoff * 2) > 10:
                backoff = 1

    async def run_once(self):
        serialized = json.dumps(dataclasses.asdict(self.config))
        self.worker = await asyncio.create_subprocess_exec(
            'python3', '-m', 'streaming.monitoring.thresholds.monitor', serialized,
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        await asyncio.gather(*[
            self._listen(self.worker.stdout, 'OUT'), self._listen(self.worker.stderr, 'ERR')
        ])

    async def stop(self):
        self.running = False
        self.worker.kill()
        await self.worker.wait()
        logging.info(f'{self.uid} shutdown')

    async def _listen(self, stream, what):
        while self.worker.returncode is None:
            line = (await stream.readline()).decode()
            if not line:
                await asyncio.sleep(1)
            else:
                logging.info(f'{self.uid}: {line}')

        logging.info(f'{self.uid}: {what} listener stopped')
