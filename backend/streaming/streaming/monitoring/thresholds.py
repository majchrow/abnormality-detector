import json
import os
import sys
import time
from json import JSONDecodeError

worker_dir = os.path.dirname(os.path.realpath(__file__))


def worker():
    while True:
        line = sys.stdin.readline()
        if line == 'POISON':
            return 0

        try:
            payload = json.loads(line)
        except JSONDecodeError:
            continue  # TODO: send back error response?

        conf_id, criteria = payload['conf_id'], payload['criteria']

        # TODO:
        for _ in range(15):
            dummy = f"I'm dumb so here're your criteria: {criteria}"
            response = {'conf_id': conf_id, 'dummy': dummy}
            sys.stdout.write(json.dumps(response) + '\n')
            sys.stdout.flush()
            time.sleep(2)


if __name__ == '__main__':
    worker()
