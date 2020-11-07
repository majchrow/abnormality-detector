import logging
import os
import sys
from argparse import ArgumentParser, ArgumentTypeError

from .config import Config
from .manager import ClientManager


# Argument types
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


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--addresses',
                        type=address,
                        required=True,
                        nargs='+',
                        metavar='ADDRESS',
                        help='bridge server addresses')
    parser.add_argument('--logfile',
                        type=str,
                        default='client_log.json',
                        help='default client logfile')
    return parser.parse_args()


def main():
    try:
        login, password = os.environ["BRIDGE_USERNAME"], os.environ["BRIDGE_PASSWORD"]
    except KeyError as e:
        print("Required USERNAME and PASSWORD environmental variables")
        sys.exit(1)

    logging.basicConfig(level=logging.INFO)
    args = parse_args()
    config = Config(
        login=login, password=password, addresses=args.addresses, logfile=args.logfile
    )

    manager = ClientManager(config)
    manager.start()


if __name__ == '__main__':
    main()
