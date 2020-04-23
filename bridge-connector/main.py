import argparse

from server import Server


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host',
                        type=str,
                        default='localhost',
                        help='host ip')
    parser.add_argument('--port',
                        type=int,
                        default=11111,
                        help='port number')
    return parser


if __name__ == '__main__':
    parser = create_parser()
    FLAGS = parser.parse_args()
    server = Server(FLAGS)
