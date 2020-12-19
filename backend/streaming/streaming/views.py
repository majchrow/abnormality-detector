import json
from json import JSONDecodeError
from aiohttp import web
from aiohttp_sse import sse_response
from dateutil.parser import ParserError, parse
from pydantic import ValidationError


__all__ = [
    'schedule_training', 'schedule_inference', 'unschedule_inference', 'run_inference', 'is_anomaly_monitored',
    'schedule_monitoring', 'cancel_monitoring', 'get_all_monitoring', 'is_monitored', 'run_monitoring',
    'get_call_info_notifications', 'get_monitoring_notifications'
]


# TODO:
#  - TEST CASES, no manual curling!
#  - reasons for HTTP 400
async def schedule_training(request):
    if (conf_name := request.match_info.get('conf_name', None)) is None:
        raise web.HTTPBadRequest(reason='no conference name given')

    try:
        payload = await request.json()
        calls = payload['calls']
        threshold = float(payload['threshold'])
    except JSONDecodeError:
        raise web.HTTPBadRequest(reason='Failed to parse JSON')
    except KeyError:
        raise web.HTTPBadRequest(reason='fields "calls" and "threshold" are mandatory')

    manager = request.app['monitoring']
    try:
        await manager.schedule_training(conf_name, calls, threshold)
        return web.Response()
    except ValidationError as e:
        return web.HTTPBadRequest(reason=str(e))


async def schedule_inference(request):
    if (conf_name := request.match_info.get('conf_name', None)) is None:
        raise web.HTTPBadRequest(reason='no conference name given')

    manager = request.app['monitoring']
    await manager.schedule_inference(conf_name)
    return web.Response()


async def unschedule_inference(request):
    if (conf_name := request.match_info.get('conf_name', None)) is None:
        raise web.HTTPBadRequest(reason='No conference name given')

    manager = request.app['monitoring']
    await manager.unschedule_inference(conf_name)
    return web.Response()


async def run_inference(request):
    if (conf_name := request.match_info.get('conf_name', None)) is None:
        raise web.HTTPBadRequest(reason='no meeting name given')

    try:
        payload = await request.json()
        # training_calls = list(map(parse, payload['training_calls']))
        start, end = parse(payload['start']), parse(payload['end'])
        threshold = float(payload['threshold'])
    except JSONDecodeError:
        raise web.HTTPBadRequest(reason='Failed to parse JSON')
    except KeyError:
        raise web.HTTPBadRequest(reason='fields "calls" and "threshold" are mandatory')
    except ParserError:
        return web.HTTPBadRequest(reason=f'invalid date format')

    manager = request.app['monitoring']
    await manager.run_inference(conf_name, payload['training_calls'], start, end, threshold)
    return web.Response()


async def run_monitoring(request):
    if (conf_name := request.match_info.get('conf_name', None)) is None:
        raise web.HTTPBadRequest(reason='no meeting name given')

    try:
        payload = await request.json()
        training_calls = list(map(parse, payload['training_calls']))
        start, end = parse(payload['start']), parse(payload['end'])
        threshold = float(payload['threshold'])
    except JSONDecodeError:
        raise web.HTTPBadRequest(reason='Failed to parse JSON')
    except KeyError:
        raise web.HTTPBadRequest(reason='fields "calls" and "threshold" are mandatory')
    except ParserError:
        return web.HTTPBadRequest(reason=f'invalid date format')

    manager = request.app['monitoring']
    await manager.run_inference(conf_name, training_calls, start, end, threshold)
    return web.Response()

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


async def cancel_monitoring(request):
    if (conf_name := request.match_info.get('conf_name', None)) is None:
        raise web.HTTPBadRequest(reason='No conference name given')

    manager = request.app['monitoring']
    await manager.unschedule_monitoring(conf_name)
    return web.Response()


async def get_all_monitoring(request):
    manager = request.app['monitoring']
    return web.json_response({'monitored': await manager.get_all_monitored()})


async def is_monitored(request):
    if (conf_name := request.match_info.get('conf_name', None)) is None:
        raise web.HTTPBadRequest(reason='No conference name given')

    manager = request.app['monitoring']
    return web.json_response({'monitored': await manager.is_monitored(conf_name)})


async def is_anomaly_monitored(request):
    if (conf_name := request.match_info.get('conf_name', None)) is None:
        raise web.HTTPBadRequest(reason='No conference name given')

    manager = request.app['monitoring']
    return web.json_response({'monitored': await manager.is_anomaly_monitored(conf_name)})


async def get_monitoring_notifications(request):
    if (conf_name := request.match_info.get('conf_name', None)) is None:
        raise web.HTTPBadRequest(reason='No conference name given')

    manager = request.app['monitoring']

    monitoring_receiver = await manager.monitoring_receiver(conf_name)
    async with sse_response(request) as resp:
        with monitoring_receiver() as receiver:
            async for anomalies in receiver():
                await resp.send(json.dumps(anomalies))
    return resp


async def get_call_info_notifications(request: web.Request):
    manager = request.app['monitoring']

    async with sse_response(request) as resp:
        with manager.calls_receiver() as receiver:
            async for data in receiver():
                await resp.send(json.dumps(data))
    return resp
