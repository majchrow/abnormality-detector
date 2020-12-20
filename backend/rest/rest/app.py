import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timezone
from flask import Flask
from flask.json import JSONEncoder
from flask_cors import CORS
import jinja2
import pytz

from .bridge import setup_bridge_dao
from .config import Config
from .db import setup_db
from .kafka import setup_kafka
from .resources import setup_resources


class ISODateJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.replace(tzinfo=timezone.utc).astimezone(tz=pytz.timezone('Europe/Warsaw')).isoformat()

        return super().default(o)


def create_app():
    app = Flask(__name__)
    app.jinja_loader = jinja2.FileSystemLoader('/flask/rest/resources')
    app.config['JSON_AS_ASCII'] = False
    app.json_encoder = ISODateJSONEncoder
    app.scheduler = BackgroundScheduler()

    config = Config()
    setup_resources(app)
    setup_db(config)
    setup_bridge_dao(app, config)
    setup_kafka(config)
    CORS(app)

    app.scheduler.start()
    atexit.register(lambda: app.scheduler.shutdown())

    return app


if __name__ == "__main__":
    create_app().run()
