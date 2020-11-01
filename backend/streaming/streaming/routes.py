import asyncio
from datetime import datetime

import aiohttp_cors
from aiohttp import web
from aiohttp_sse import sse_response

routes = web.RouteTableDef()


@routes.get('/notifications/{conf_id}')
async def anomaly_notifications(request):
    loop = request.app.loop
    async with sse_response(request) as resp:
        while True:
            data = f'{request.match_info["conf_id"]} : {datetime.now()}'
            await resp.send(data)
            await asyncio.sleep(1, loop=loop)
    return resp


def setup_routes(app: web.Application):
    app.add_routes(routes)


def setup_cors(app: web.Application):
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })
    for route in app.router.routes():
        cors.add(route)
