import atexit
import os
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from flask_cors import CORS
import os
import jinja2

from .bridge import setup_bridge_dao
from .config import Config
from .db import setup_db
from .resources import setup_resources


def create_app():
    app = Flask(__name__)
    app.jinja_loader = jinja2.FileSystemLoader('/flask/rest/resources')
    app.config['JSON_AS_ASCII'] = False
    app.scheduler = BackgroundScheduler()

    config = Config()
    setup_resources(app)
    setup_db(config)
    setup_bridge_dao(app, config)
    CORS(app)

    app.scheduler.start()
    atexit.register(lambda: app.scheduler.shutdown())

    return app


if __name__ == "__main__":
    create_app().run()