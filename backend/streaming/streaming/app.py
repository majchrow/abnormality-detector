from aiohttp import web

from .routes import setup_cors, setup_routes


def create_app():
    app = web.Application()
    setup_routes(app)
    setup_cors(app)

    return app


if __name__ == '__main__':
    web.run_app(create_app())
