from flask import Flask
from flask_cors import CORS
import os

from .db import setup_db
from .resources import setup_resources


def create_app():
    app = Flask(__name__)
    host = os.environ["CASSANDRA_HOST"]
    port = os.environ["CASSANDRA_PORT"]
    user = os.environ["CASSANDRA_USER"]
    passwd = os.environ["CASSANDRA_PASSWD"]
    keyspace = os.environ["KEYSPACE"]
    calls_table = os.environ["CALLS_TABLE"]
    setup_resources(app)
    setup_db(host, port, user, passwd, keyspace, calls_table)
    CORS(app)
    return app


if __name__ == "__main__":
    create_app().run()
