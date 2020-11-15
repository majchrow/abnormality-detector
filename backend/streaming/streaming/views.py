from json import JSONDecodeError
from aiohttp import web
from aiohttp_sse import sse_response

from .exceptions import UnmonitoredError

__all__ = ['schedule_monitoring', 'get_monitoring', 'get_all_monitoring', 'cancel_monitoring', 'get_notifications']


# TODO:
#  - TEST CASES, no manual curling!
#  - reasons for HTTP 400
async def schedule_monitoring(request):
    conf_name = request.match_info.get('conf_name', None)
    try:
        payload = await request.json()
    except JSONDecodeError:
        raise web.HTTPBadRequest(reason='Failed to parse JSON')

    manager = request.app['monitoring']
    await manager.schedule(conf_name, payload)
    return web.Response()


async def get_monitoring(request: web.Request):
    conf_name = request.rel_url.query.get('conf_name', None)
    monitoring_type = request.rel_url.query.get('type', None)

    if monitoring_type is None:
        raise web.HTTPBadRequest()

    manager = request.app['monitoring']
    import logging
    logging.info(conf_name)
    criteria = await manager.get_criteria(conf_name, monitoring_type)
    return web.json_response(criteria)


async def get_all_monitoring(request: web.Request):
    manager = request.app['monitoring']
    criteria = await manager.get_all_criteria()
    return web.json_response(criteria)


async def cancel_monitoring(request):
    conf_name = request.match_info.get('conf_name', None)
    monitoring_type = request.rel_url.query.get('type', None)

    if monitoring_type is None:
        raise web.HTTPBadRequest()

    manager = request.app['monitoring']
    try:
        await manager.unschedule(conf_name, monitoring_type)
        return web.Response()
    except UnmonitoredError:
        raise web.HTTPBadRequest(reason=f'{conf_name} not monitored!')


async def get_notifications(request):
    conf_name = request.rel_url.query.get('conf_name', None)
    manager = request.app['monitoring']

    try:
        receiver = manager.receiver(conf_name)
        async with sse_response(request) as resp:
            async for data in receiver():
                await resp.send(data)
        return resp
    except UnmonitoredError:
        raise web.HTTPBadRequest(reason=f'{conf_name} not monitored!')
