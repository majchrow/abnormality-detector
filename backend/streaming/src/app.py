import asyncio
from aiohttp import web
from aiohttp_sse import sse_response
from datetime import datetime

routes = web.RouteTableDef()


@routes.get('/notifications/{room_id}')
async def anomaly_notifications(request):
    loop = request.app.loop
    async with sse_response(request) as resp:
        while True:
            data = f'{request.match_info["room_id"]} : {datetime.now()}'
            await resp.send(data)
            await asyncio.sleep(1, loop=loop)
    return resp


def create_app():
    app = web.Application()
    app.add_routes(routes)
    return app


if __name__ == '__main__':
    web.run_app(create_app())
