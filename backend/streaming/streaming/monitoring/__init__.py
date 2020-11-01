from json import JSONDecodeError

from aiohttp import web
from aiohttp_sse import sse_response

from .manager import Manager

__all__ = ['setup_monitoring', 'get_notifications', 'schedule_monitoring']


async def schedule_monitoring(request):
    conf_id = request.match_info['conf_id']
    try:
        payload = await request.json()
    except JSONDecodeError:
        raise web.HTTPBadRequest(reason='Failed to parse JSON')

    manager = request.app['monitoring']
    await manager.dispatch(conf_id, payload)
    return web.Response()


async def get_notifications(request):
    conf_id = request.match_info['conf_id']
    queue = request.app['monitoring'].threshold_notifications_q[conf_id]  # TODO: missing key?

    async with sse_response(request) as resp:
        while True:
            data = await queue.get()
            await resp.send(data)
    return resp


async def start_all(app: web.Application):
    await app['monitoring'].start()


async def cancel_all(app: web.Application):
    await app['monitoring'].shutdown()


def setup_monitoring(app: web.Application):
    manager = Manager()
    app['monitoring'] = manager
    app.on_startup.append(start_all)
    app.on_cleanup.append(cancel_all)
