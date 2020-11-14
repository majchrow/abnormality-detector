import logging
from aiohttp import web

from .monitoring import setup_monitoring
from .routes import setup_routes


def create_app():
    logging.basicConfig(level=logging.INFO)

    app = web.Application()
    setup_routes(app)
    setup_monitoring(app)
    return app


if __name__ == '__main__':
    web.run_app(create_app())
