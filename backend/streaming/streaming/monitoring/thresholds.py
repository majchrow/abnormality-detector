import json
import os
import sys
import time
from json import JSONDecodeError

worker_dir = os.path.dirname(os.path.realpath(__file__))

# TODO:
#  - worker must die

# TODO:
#  - listen to Kafka topic for parameter values
#  - run defined conditions on each, send back (STDOUT) info about detected anomalies
#  - separate (logical) thread, listen on STDIN for new condition requests, modify collection of used conditions


def worker():
    while True:
        line = sys.stdin.readline()
        if line == 'POISON':
            return 0

        try:
            payload = json.loads(line)
        except JSONDecodeError:
            break  # TODO: send back error response?

        conf_id, criteria = payload['conf_id'], payload['criteria']

        # TODO:
        for _ in range(15):
            dummy = f"I'm dumb so here're your criteria: {criteria}"
            response = {'conf_id': conf_id, 'response': dummy}
            sys.stdout.write(json.dumps(response) + '\n')
            sys.stdout.flush()
            time.sleep(2)


if __name__ == '__main__':
    worker()
