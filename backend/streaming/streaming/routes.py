import aiohttp_cors
from aiohttp import web

from .views import cancel_monitoring, get_notifications, schedule_monitoring


def setup_routes(app: web.Application):
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })
    cors.add(app.router.add_get('/notifications/{conf_name}', get_notifications))
    cors.add(app.router.add_get('/notifications', get_notifications))

    cors.add(app.router.add_post('/monitoring/{conf_name}', schedule_monitoring))
    cors.add(app.router.add_delete('/monitoring/{conf_name}', cancel_monitoring))

    cors.add(app.router.add_post('/monitoring', schedule_monitoring))
    cors.add(app.router.add_delete('/monitoring', cancel_monitoring))
