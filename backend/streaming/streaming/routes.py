import aiohttp_cors
from aiohttp import web

from .views import *


def setup_routes(app: web.Application):
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })
    cors.add(app.router.add_put('/monitoring/{conf_name}', schedule_monitoring))
    cors.add(app.router.add_delete('/monitoring/{conf_name}', cancel_monitoring))
    cors.add(app.router.add_get('/monitoring/{conf_name}', is_monitored))
    cors.add(app.router.add_get('/monitoring', get_all_monitoring))

    cors.add(app.router.add_get('/notifications/{conf_name}', get_monitoring_notifications))
    cors.add(app.router.add_get('/notifications', get_call_info_notifications))
