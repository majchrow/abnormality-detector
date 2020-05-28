import os
import sys
from argparse import ArgumentParser

from client import Client


def create_parser():
    parser = ArgumentParser()
    parser.add_argument('--host',
                        type=str,
                        default='localhost',
                        help='host ip')
    parser.add_argument('--port',
                        type=int,
                        default=445,
                        help='port number')
    parser.add_argument('--logfile',
                        type=str,
                        default='client_log.json',
                        help='default client logfile')
    return parser


if __name__ == '__main__':
    try:
        os.environ["BRIDGE_USERNAME"] and os.environ["BRIDGE_PASSWORD"]
    except KeyError as e:
        print("Required USERNAME and PASSWORD environmental variables")
        sys.exit(1)

    parser = create_parser()
    FLAGS = parser.parse_args()
    client = Client(FLAGS)
    client.start()
