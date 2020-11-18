import logging
from aiohttp import web

from .config import Config
from .db import setup_db
from .monitoring.manager import setup_monitoring
from .routes import setup_routes


def create_app():
    logging.basicConfig(level=logging.INFO)

    # TODO: config file/cmd line
    config = Config(
        kafka_topic_map={
            'preprocessed_callInfoUpdate': 'callInfoUpdate',
            'preprocessed_rosterUpdate': 'rosterUpdate',
            'preprocessed_callListUpdate': 'callListUpdate'
        }
    )

    app = web.Application()
    setup_routes(app)
    setup_db(app, config)
    setup_monitoring(app, config)
    return app


if __name__ == '__main__':
    web.run_app(create_app())
