import asyncio
import json
import logging
import os
import sys
import time
from json import JSONDecodeError

from .protocol import AsyncStreams

worker_dir = os.path.dirname(os.path.realpath(__file__))


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
        self.listener = asyncio.create_task(self._listen())

    async def _listen(self):
        while self.running:
            line = await AsyncStreams.read_str(self.worker.stdout)

            if not line:
                logging.info('Threshold worker process shutdown!')  # TODO: handle possible errors
                break

            payload = json.loads(line)
            conf_id, response = payload['conf_id'], payload['response']
            await self.notification_q[conf_id].put(response)

    async def _monitor(self):
        while self.running:
            line = await AsyncStreams.read_str(self.worker.stderr)
            if line:
                logging.error(f'Error in worker subprocess: {line}')

    async def submit(self, conf_id: str, criteria: dict):
        # TODO:
        #  - save it to DB
        #  - on start - check if there are some criteria in DB
        payload = {'conf_id': conf_id, 'criteria': criteria}
        await AsyncStreams.send_dict(payload, self.worker.stdin)

    async def shutdown(self):
        self.running = False
        await AsyncStreams.send_str('POISON', self.worker.stdin)
        await self.worker.wait()
        logging.info('Threshold worker process stopped.')

        self.listener.cancel()
        await self.listener
        logging.info('Threshold worker manager task stopped.')


# TODO:
#  - worker must die properly

# TODO: (real behavior)
#  (threads or coroutines?)
#  - thread 1:
#    - listen to Kafka topic for parameter values
#    - run defined conditions on each, send back (STDOUT) info about detected anomalies
#  - thread 2:
#    - listen on STDIN for new condition requests, modify collection of used conditions


def worker():
    while True:
        line = sys.stdin.readline()
        if line == 'POISON':
            sys.stdout.write('Received poison pill, farewell\n')
            sys.stdout.flush()
            return 0

        try:
            payload = json.loads(line)
        except JSONDecodeError:
            break  # TODO: send back error response?

        conf_id, criteria = payload['conf_id'], payload['criteria']

        # TODO:
        for _ in range(5):
            dummy = f"I'm dumb so here're your criteria: {criteria}"
            response = {'conf_id': conf_id, 'response': dummy}
            sys.stdout.write(json.dumps(response) + '\n')
            sys.stdout.flush()
            time.sleep(1)
        raise Exception


if __name__ == '__main__':
    worker()
