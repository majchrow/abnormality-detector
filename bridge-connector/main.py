from argparse import ArgumentParser

from client import Client
from server import Server


def create_parser():
    parser = ArgumentParser()
    parser.add_argument('--host',
                        type=str,
                        default='localhost',
                        help='host ip')
    parser.add_argument('--username',
                        type=str,
                        help='username account with sufficient privilege')
    parser.add_argument('--password',
                        type=str,
                        help='password account with sufficient privilege ')
    parser.add_argument('--logfile',
                        type=str,
                        default='log.json',
                        help='logfile')
    parser.add_argument('--port',
                        type=int,
                        default=12345,
                        help='port number')
    parser.add_argument('--server',
                        dest='server',
                        action='store_true',
                        help='run server, by default runs client')
    return parser


if __name__ == '__main__':
    parser = create_parser()
    FLAGS = parser.parse_args()
    assert FLAGS.server or FLAGS.auth_token, "Authentication token is required for client"
    if FLAGS.server:
        server = Server(FLAGS)
        server.start()
    else:
        client = Client(FLAGS)
        client.start()
