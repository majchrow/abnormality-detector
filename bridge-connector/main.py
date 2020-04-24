from argparse import ArgumentParser

from client import Client
from server import Server


def create_parser():
    parser = ArgumentParser()
    parser.add_argument('--host',
                        type=str,
                        default='localhost',
                        help='host ip')
    parser.add_argument('--logfile',
                        type=str,
                        default='log.json',
                        help='host ip')
    parser.add_argument('--port',
                        type=int,
                        default=12345,
                        help='port number')
    parser.add_argument('--client',
                        dest='client',
                        action='store_true',
                        help='run client, if not set run server')
    return parser


if __name__ == '__main__':
    parser = create_parser()
    FLAGS = parser.parse_args()
    if FLAGS.client:
        client = Client(FLAGS)
        client.start()
    else:
        server = Server(FLAGS)
        server.start()
