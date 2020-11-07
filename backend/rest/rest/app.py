from flask import Flask
from flask_cors import CORS

from .db import setup_db
from .resources import setup_resources


def create_app():
    app = Flask(__name__)

    # TODO: app.config for Cassandra cluster
    setup_resources(app)
    setup_db(app)
    CORS(app)

    return app


if __name__ == '__main__':
    create_app().run()
