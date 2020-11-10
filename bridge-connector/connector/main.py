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
    parser.add_argument('--kafka-file',
                        type=str,
                        default='client_kafka.json',
                        help='file to dump messages as they shall be published to Kafka')
    return parser.parse_args()


# TODO:
#  - one instance with 4 servers & full debug logging to file
#    to test if the app doesn't break with multiple conversations
#  - another instance with 1 server and saving all server communication
#    to file for simulation with out server later, info logging to stdout
#  - for later: an option to run with Kafka producer 
def main():
    try:
        login, password = os.environ["BRIDGE_USERNAME"], os.environ["BRIDGE_PASSWORD"]
    except KeyError:
        print("Required BRIDGE_USERNAME and BRIDGE_PASSWORD environmental variables")
        sys.exit(1)

    args = parse_args()
    config = Config(
        login=login, password=password, addresses=args.addresses,
        logfile=args.logfile, dumpfile=args.dumpfile, kafka_file=args.kafka_file
    )

    log_to_file(config.logfile, level=logging.INFO)

    manager = ClientManager(config)
    manager.start()


if __name__ == '__main__':
    main()
