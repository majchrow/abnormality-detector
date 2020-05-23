from argparse import ArgumentParser

from client import Client


def create_parser():
    parser = ArgumentParser()
    parser.add_argument('--host',
                        type=str,
                        default='localhost',
                        help='host ip')
    parser.add_argument('--username',
                        type=str,
                        required=True,
                        help='username account with sufficient privilege')
    parser.add_argument('--password',
                        type=str,
                        required=True,
                        help='password account with sufficient privilege ')
    parser.add_argument('--port',
                        type=int,
                        default=12345,
                        help='port number')
    return parser


if __name__ == '__main__':
    parser = create_parser()
    FLAGS = parser.parse_args()
    client = Client(FLAGS)
    client.start()
