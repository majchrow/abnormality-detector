import asyncio
import logging
from typing import List


class BaseWorkerManager:

    TAG = 'BaseWorkerManager'

    def __init__(self):
        self.cmd = []
        self.num_workers = None
        self.worker_id = None

        self.workers = []
        self.started = asyncio.Event()

    async def run(self):
        for i in range(self.num_workers):
            worker = ChildProcess(f'{self.worker_id}-{i}', self.cmd)
            self.workers.append(worker)
        asyncio.create_task(self.set_started())
        await asyncio.gather(*[w.run() for w in self.workers], return_exceptions=True)

    async def set_started(self):
        await asyncio.gather(*[w.started.wait() for w in self.workers], return_exceptions=True)
        await asyncio.sleep(3)
        self.started.set()

    async def shutdown(self):
        await asyncio.gather(*[w.stop() for w in self.workers])
        logging.info(f'{self.TAG}: shutdown')


class ChildProcess:
    def __init__(self, uid: str, cmd: List[str]):
        self.uid = uid
        self.cmd = cmd
        self.running = True
        self.worker = None
        self.task = None
        self.started = asyncio.Event()

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
        self.worker = await asyncio.create_subprocess_exec(
            *self.cmd,
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
        fst_line = (await stream.readline()).decode()
        if 'started' in fst_line:
            self.started.set()
            logging.info(f'{self.uid}: {fst_line.strip()}')

        while self.worker.returncode is None:
            line = (await stream.readline()).decode().strip()
            if not line:
                await asyncio.sleep(1)
            else:
                logging.info(f'{self.uid}: {line}')

        logging.info(f'{self.uid}: {what} listener stopped')


async def run_for_result(uid: str, cmd: List[str]):
    async def listen(stream, what):
        while worker.returncode is None:
            line = (await stream.readline()).decode()
            if not line:
                await asyncio.sleep(1)
            else:
                logging.info(f'{uid}: {line}')

        logging.info(f'{uid}: {what} listener stopped')

    worker = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    out_task = asyncio.create_task(listen(worker.stdout, 'OUT'))
    err_task = asyncio.create_task(listen(worker.stdout, 'ERR'))

    await worker.wait()
    out_task.cancel()
    err_task.cancel()
    await out_task
    await err_task
