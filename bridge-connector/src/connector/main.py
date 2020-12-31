import logging
import os
import sys
from argparse import ArgumentParser, ArgumentTypeError

from .config import Config
from .client import ClientManager
from .utils import log_to_file


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
                        help='default file for logging module')
    parser.add_argument('--dumpfile',
                        type=str,
                        default='client_dump.json',
                        help='default file to dump all raw server communication')
    parser.add_argument('--kafka-bootstrap-server',
                        type=str,
                        help='address of Kafka bootstrap server, e.g. localhost:9092')
    parser.add_argument('--no-ssl',
                        action='store_false',
                        dest='ssl',
                        help='disable SSL for HTTP and WebSocket connection - for testing purposes only')
    return parser.parse_args()


def main():
    try:
        login, password = os.environ["BRIDGE_USER"], os.environ["BRIDGE_PASSWORD"]
    except KeyError:
        print("Required BRIDGE_USER and BRIDGE_PASSWORD environmental variables")
        sys.exit(1)

    args = parse_args()
    config = Config(
        login=login, password=password,
        addresses=args.addresses, kafka_bootstrap_address=args.kafka_bootstrap_server,
        logfile=args.logfile, dumpfile=args.dumpfile, ssl=args.ssl
    )

    log_to_file(config.logfile, level=logging.INFO)

    manager = ClientManager(config)
    manager.start()


if __name__ == '__main__':
    main()
