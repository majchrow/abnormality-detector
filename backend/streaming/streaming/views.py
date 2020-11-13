from json import JSONDecodeError
from aiohttp import web
from aiohttp_sse import sse_response

from .monitoring.manager import Manager


async def schedule_monitoring(request):
    conf_name = request.match_info.get('conf_name', None)
    try:
        payload = await request.json()
    except JSONDecodeError:
        raise web.HTTPBadRequest(reason='Failed to parse JSON')

    manager = request.app['monitoring']
    monitoring_key = ('SINGLE', conf_name) if conf_name else ('ALL', 'ALL')

    await manager.schedule(monitoring_key, payload)
    return web.Response()


async def cancel_monitoring(request):
    conf_name = request.match_info.get('conf_name', None)
    manager = request.app['monitoring']
    monitoring_key = ('SINGLE', conf_name) if conf_name else ('ALL', 'ALL')

    await manager.unschedule(monitoring_key)
    return web.Response()


async def get_notifications(request):
    conf_name = request.match_info['conf_name']
    manager = request.app['monitoring']

    # TODO: handle non-monitored conference case
    try:
        async with sse_response(request) as resp:
            async for data in manager.receive(conf_name):
                await resp.send(data)
        return resp
    except Manager.UnmonitoredError:
        raise web.HTTPBadRequest()
