import json
from json import JSONDecodeError
from aiohttp import web
from aiohttp_sse import sse_response
from pydantic import ValidationError

from .exceptions import (
    DBFailureError, ModelNotExistsError, MeetingNotExistsError, MeetingNotExistsError, UnmonitoredError
)

__all__ = [
    'schedule_training', 'schedule_inference', 'unschedule_inference',
    'schedule_monitoring', 'cancel_monitoring', 'get_all_monitoring', 'is_monitored',
    'get_call_info_notifications', 'get_monitoring_notifications'
]


# TODO:
#  - TEST CASES, no manual curling!
#  - reasons for HTTP 400
#  - MonitoringNotSupportedError for all endpoints?
async def schedule_training(request):
    if (conf_name := request.match_info.get('conf_name', None)) is None:
        raise web.HTTPBadRequest(reason='no conference name given')

    try:
        payload = await request.json()
        calls = payload['calls']
    except JSONDecodeError:
        raise web.HTTPBadRequest(reason='Failed to parse JSON')
    except KeyError:
        raise web.HTTPBadRequest(reason='field "calls" is mandatory')

    manager = request.app['monitoring']
    try:
        await manager.schedule_training(conf_name, calls)
        return web.Response()
    except ValidationError as e:
        return web.HTTPBadRequest(reason=str(e))
    except MeetingNotExistsError:
        raise web.HTTPBadRequest(reason=f'meeting {conf_name} does not exist')


async def schedule_inference(request):
    if (conf_name := request.match_info.get('conf_name', None)) is None:
        raise web.HTTPBadRequest(reason='no conference name given')

    manager = request.app['monitoring']
    try:
        await manager.schedule_inference(conf_name)
        return web.Response()
    except MeetingNotExistsError:
        raise web.HTTPBadRequest(reason=f'meeting {conf_name} does not exist')
    except ModelNotExistsError:
        raise web.HTTPBadRequest(reason=f'no model found for {conf_name}')


async def unschedule_inference(request):
    if (conf_name := request.match_info.get('conf_name', None)) is None:
        raise web.HTTPBadRequest(reason='No conference name given')

    manager = request.app['monitoring']
    try:
        await manager.unschedule_inference(conf_name)
        return web.Response()
    except MeetingNotExistsError:
        raise web.HTTPBadRequest(reason=f'meeting {conf_name} does not exist')
    except UnmonitoredError:
        raise web.HTTPBadRequest(reason=f'meeting {conf_name} is not monitored')


async def schedule_monitoring(request):
    # TODO: meeting_name, not conf_name
    # TODO: type not necessary anymore
    if (conf_name := request.match_info.get('conf_name', None)) is None:
        raise web.HTTPBadRequest(reason='No conference name given')

    try:
        payload = await request.json()
        criteria = payload['criteria']
    except JSONDecodeError:
        raise web.HTTPBadRequest(reason='Failed to parse JSON')
    except KeyError:
        raise web.HTTPBadRequest(reason='field "criteria" is mandatory')

    manager = request.app['monitoring']
    try:
        await manager.schedule_monitoring(conf_name, criteria)
        return web.Response()
    except ValidationError as e:
        return web.HTTPBadRequest(reason=str(e))
    except MeetingNotExistsError:
        raise web.HTTPBadRequest(reason=f'room {conf_name} does not exist')
    except DBFailureError:
        return web.HTTPInternalServerError(reason='DB operation failed')


async def cancel_monitoring(request):
    if (conf_name := request.match_info.get('conf_name', None)) is None:
        raise web.HTTPBadRequest(reason='No conference name given')

    manager = request.app['monitoring']
    try:
        await manager.unschedule_monitoring(conf_name)
        return web.Response()
    except UnmonitoredError:
        raise web.HTTPBadRequest(reason=f'{conf_name} not monitored!')
    except DBFailureError:
        return web.HTTPInternalServerError(reason='DB operation failed')


async def get_all_monitoring(request):
    manager = request.app['monitoring']
    return web.json_response({'monitored': await manager.get_all_monitored()})


async def is_monitored(request):
    if (conf_name := request.match_info.get('conf_name', None)) is None:
        raise web.HTTPBadRequest(reason='No conference name given')

    manager = request.app['monitoring']
    return web.json_response({'monitored': await manager.is_monitored(conf_name)})


async def get_monitoring_notifications(request):
    if (conf_name := request.match_info.get('conf_name', None)) is None:
        raise web.HTTPBadRequest(reason='No conference name given')

    manager = request.app['monitoring']

    try:
        monitoring_receiver = await manager.monitoring_receiver(conf_name)
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
