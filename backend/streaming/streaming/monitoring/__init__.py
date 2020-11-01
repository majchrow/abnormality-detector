from json import JSONDecodeError

from aiohttp import web
from aiohttp_sse import sse_response
from pydantic import ValidationError

from .manager import Manager
from .protocol import MonitoringRequest

__all__ = ['setup_monitoring', 'get_notifications', 'schedule_monitoring']


# TODO: add typing!
async def schedule_monitoring(request):
    conf_id = request.match_info['conf_id']
    try:
        payload = await request.json()
        m_request = MonitoringRequest.parse_obj(payload)
    except JSONDecodeError:
        raise web.HTTPBadRequest(reason='Failed to parse JSON')
    except ValidationError as e:
        raise web.HTTPBadRequest(reason=str(e))

    manager = request.app['monitoring']
    await manager.dispatch(conf_id, m_request)
    return web.Response()


async def get_notifications(request):
    conf_id = request.match_info['conf_id']
    queue = request.app['monitoring'].notify_threshold_q[conf_id]  # TODO: missing key?

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
