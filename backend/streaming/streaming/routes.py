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

    # Get all criteria (defined by all received requests)
    cors.add(app.router.add_get('/monitoring/all', get_all_monitoring))

    # TODO: delete all monitoring (defined by all requests)?
    # cors.add(app.router.add_delete('/monitoring/all', cancel_all_monitoring))

    # Get criteria defined by a single request (for single conference or for all conferences)
    cors.add(app.router.add_get('/monitoring', get_monitoring))

    cors.add(app.router.add_put('/monitoring/{conf_name}', schedule_monitoring))
    cors.add(app.router.add_put('/monitoring', schedule_monitoring))

    cors.add(app.router.add_delete('/monitoring/{conf_name}', cancel_monitoring))
    cors.add(app.router.add_delete('/monitoring', cancel_monitoring))

    # Get notifications for criteria defined by a single request (for single conference or for all conferences)
    cors.add(app.router.add_get('/notifications', get_notifications))

