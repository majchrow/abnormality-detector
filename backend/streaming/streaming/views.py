import json
from json import JSONDecodeError
from aiohttp import web
from aiohttp_sse import sse_response

from .exceptions import MonitoringNotSupportedError, UnmonitoredError

__all__ = [
    'schedule_monitoring', 'cancel_monitoring', 'get_all_monitoring', 'is_monitored', 'get_call_info_notifications',
    'get_monitoring_notifications'
]


# TODO:
#  - TEST CASES, no manual curling!
#  - reasons for HTTP 400
#  - MonitoringNotSupportedError for all endpoints?
async def schedule_monitoring(request):
    if (conf_name := request.match_info.get('conf_name', None)) is None:
        raise web.HTTPBadRequest(reason='No conference name given')

    try:
        payload = await request.json()
    except JSONDecodeError:
        raise web.HTTPBadRequest(reason='Failed to parse JSON')

    manager = request.app['monitoring']
    try:
        await manager.schedule(conf_name, payload)
        return web.Response()
    except ValueError as e:
        return web.HTTPBadRequest(reason=str(e))


async def cancel_monitoring(request):
    if (conf_name := request.match_info.get('conf_name', None)) is None:
        raise web.HTTPBadRequest(reason='No conference name given')
    if (monitoring_type := request.rel_url.query.get('type', None)) is None:
        raise web.HTTPBadRequest(reason='Missing "type" query parameter')

    manager = request.app['monitoring']
    try:
        await manager.unschedule(conf_name, monitoring_type)
        return web.Response()
    except UnmonitoredError:
        raise web.HTTPBadRequest(reason=f'{conf_name} not monitored!')
    except MonitoringNotSupportedError:
        raise web.HTTPBadRequest(reason=f'{monitoring_type} is not supported!')


async def get_all_monitoring(request):
    manager = request.app['monitoring']
    return web.json_response({'monitored': manager.get_all_monitored()})


async def is_monitored(request):
    if (conf_name := request.match_info.get('conf_name', None)) is None:
        raise web.HTTPBadRequest(reason='No conference name given')

    manager = request.app['monitoring']
    return web.json_response({'monitored': manager.is_monitored(conf_name)})


async def get_monitoring_notifications(request):
    if (conf_name := request.match_info.get('conf_name', None)) is None:
        raise web.HTTPBadRequest(reason='No conference name given')
    if (monitoring_type := request.rel_url.query.get('type', None)) is None:
        raise web.HTTPBadRequest(reason='Missing "type" query parameter')

    manager = request.app['monitoring']

    try:
        monitoring_receiver = manager.monitoring_receiver(conf_name, monitoring_type)
        async with sse_response(request) as resp:
            with monitoring_receiver() as receiver:
                async for anomalies in receiver():
                    await resp.send(json.dumps(anomalies))
        return resp
    except UnmonitoredError:
        raise web.HTTPBadRequest(reason=f'{conf_name} not monitored!')


async def get_call_info_notifications(request: web.Request):
    manager = request.app['monitoring']

    async with sse_response(request) as resp:
        with manager.calls_receiver() as receiver:
            async for data in receiver():
                await resp.send(json.dumps(data))
    return resp

