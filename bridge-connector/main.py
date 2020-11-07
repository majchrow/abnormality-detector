import logging
import os
import sys
from argparse import ArgumentParser, ArgumentTypeError

from config import Config
from connector.manager import ClientManager


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


def positive_int(arg):
    val = int(arg)
    if val <= 0:
        raise ArgumentTypeError(f'Argument must be a positibe integer')
    return val


def parse_config():
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
    parser.add_argument('--max-ws-connections',
                        type=positive_int,
                        default=5,
                        help='max number of WebSockets per server')
    args = parser.parse_args()
    return Config(
        login=login, password=password, addresses=args.addresses,
        logfile=args.logfile, max_ws_connections=args.max_ws_connections
    )


if __name__ == '__main__':
    try:
        login, password = os.environ["BRIDGE_USERNAME"], os.environ["BRIDGE_PASSWORD"]
    except KeyError as e:
        print("Required USERNAME and PASSWORD environmental variables")
        sys.exit(1)
   
    logging.basicConfig(level=logging.INFO)
    config = parse_config()
    manager = ClientManager(config)
    manager.start()
