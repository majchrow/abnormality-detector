import logging
from aiohttp import web

from .config import Config
from .db import setup_db
from .exceptions import error_middleware
from .monitoring.managers import setup_monitoring
from .routes import setup_routes


def create_app():
    logging.basicConfig(format='%(levelname)s %(asctime)s: %(message)s', level=logging.INFO)
    config = Config()

    app = web.Application(middlewares=[error_middleware])
    setup_routes(app)
    setup_db(app, config)
    setup_monitoring(app, config)
    return app


if __name__ == '__main__':
    web.run_app(create_app())
