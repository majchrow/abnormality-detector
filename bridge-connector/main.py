import os
import sys
from argparse import ArgumentParser, ArgumentTypeError

from connector.manager import ClientManager


def address(arg):
    try:
        host, port = arg.split(':')
    except ValueError:
        raise ArgumentTypeError("Address must be in host:port format")
    try:
        port = int(port)
        assert port > 0
    except (ValueError, AssertionError):
        raise ArgumentTypeError("Port must be a positive integer")

    return host, port


def create_parser():
    parser = ArgumentParser()
    parser.add_argument('--addresses',
                        type=address,
                        nargs='+',
                        help='bridge server addresses')
    parser.add_argument('--logfile',
                        type=str,
                        default='client_log.json',
                        help='default client logfile')
    parser.add_argument('--max-ws-count',
                        type=int,
                        default=5,
                        help='max number of WebSockets per server')
    return parser


if __name__ == '__main__':
    try:
        login, password = os.environ["BRIDGE_USERNAME"], os.environ["BRIDGE_PASSWORD"]
    except KeyError as e:
        print("Required USERNAME and PASSWORD environmental variables")
        sys.exit(1)

    parser = create_parser()
    config = parser.parse_args()
    conn = ClientManager(login, password, config)
    conn.start()
