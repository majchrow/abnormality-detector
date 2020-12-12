from flask import Flask
from flask_cors import CORS
import os
import jinja2

from .config import Config
from .db import setup_db
from .resources import setup_resources


def create_app():
    app = Flask(__name__)
    app.jinja_loader = jinja2.FileSystemLoader('/flask/rest/resources/output')
    config = Config()
    setup_resources(app)
    setup_db(config)
    CORS(app)
    return app


if __name__ == "__main__":
    create_app().run()