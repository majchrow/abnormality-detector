import aiohttp_cors
from aiohttp import web

from .monitoring import *


def setup_routes(app: web.Application):
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })
    cors.add(app.router.add_get('/notifications/{conf_id}', get_notifications))
    cors.add(app.router.add_post('/monitoring/{conf_id}', schedule_monitoring))
