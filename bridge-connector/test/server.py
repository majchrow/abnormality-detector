import aiohttp
import asyncio
import json
import logging
from aiohttp import web
from itertools import cycle


class Server:
    def __init__(self, loop, username, password, dumpfile) -> None:
        self.credentials = (username, password)
        self.dumpfile = dumpfile
        self.auth_token = 'Token-of-eternal-prosperity'
        self.clients = set()
        self.call_info_clients = set()
        self.call_roaster_clients = set()
        self.calls_clients = set()
        self.call_info_data = []
        self.call_roaster_data = []
        self.calls_data = []
        self.unknown = []
        self.loop = loop
        self._prepare_data()

    async def start(self) -> None:
        self.loop.create_task(self.stream_calls())
        self.loop.create_task(self.stream_call_info())
        self.loop.create_task(self.stream_call_roaster())

    def _prepare_data(self) -> None:
        with open(self.dumpfile) as json_file:
            data = json.load(json_file)
        for message in data:
            queue = self.unknown
            if message['message']['type'] == "rosterUpdate":
                queue = self.call_roaster_data
            elif message['message']['type'] == "callInfoUpdate":
                queue = self.call_info_data
            elif message['message']['type'] == "callListUpdate":
                queue = self.calls_data
            queue.append(message)
        self.calls_data.append(
            {"type": "message", "message": {"messageId": 3, "type": "callListUpdate", "subscriptionIndex": 3,
                                            "updates": [
                                                {"call": "97c771ae-fc2e-4257-b129-30ee818e034b", "updateType": "add",
                                                 "name": "Andy'scoSpace", "participants": 0}]}}
        )

    async def token(self, request):
        credentials = aiohttp.BasicAuth.decode(request.headers['Authorization'])
        if self.credentials == (credentials.login, credentials.password):
            resp = web.Response()
            resp.headers['X-Cisco-CMS-Auth-Token'] = self.auth_token
            return resp
        else:
            raise web.HTTPUnauthorized()

    async def serve(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        if request.rel_url.query['authToken'] != self.auth_token:
            raise web.HTTPUnauthorized()

        await self.register(ws, request.remote)
        await self.handle_ws(ws, request.remote)
        await self.unregister(ws, request.remote)
        logging.info('WebSocket connection closed')

        return ws

    async def handle_ws(self, ws, remote_address):
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                if msg.data == 'close':
                    await ws.close()
                else:
                    msg_dict = json.loads(msg.data)
                    await self.handle_msg(ws, msg_dict)
                    logging.info(f"Got from {remote_address} message {msg.data}")
            elif msg.type == aiohttp.WSMsgType.ERROR:
                print(f'WebSocket connection closed with exception {ws.exception()}')

    async def handle_msg(self, ws, msg_dict):
        if 'message' not in msg_dict:
            # ignore acknowledgements
            return

        try:
            msg = msg_dict['message']
            if msg['type'] == "subscribeRequest":
                subscriptions = msg['subscriptions']
                for subscription in subscriptions:
                    if subscription['type'] == "callRoster":
                        self.call_roaster_clients.add(ws)
                    elif subscription['type'] == "callInfo":
                        self.call_info_clients.add(ws)
                    else:
                        self.calls_clients.add(ws)
        except:
            logging.exception(msg_dict)

    async def register(self, ws, remote_address) -> None:
        self.clients.add(ws)
        logging.info(f"{remote_address} connected.")

    async def unregister(self, ws, remote_address) -> None:
        self.clients.remove(ws)
        logging.info(f"{remote_address} disconnected.")

    async def stream_call_info(self) -> None:
        for data in cycle(self.call_info_data):
            logging.info(f'SENT: {data}')
            for client in self.call_info_clients:
                await client.send_json(data)
            await asyncio.sleep(2)

    async def stream_call_roaster(self) -> None:
        for data in cycle(self.call_roaster_data):
            logging.info(f'SENT: {data}')
            for client in self.call_roaster_clients:
                await client.send_json(data)
            await asyncio.sleep(2)

    async def stream_calls(self) -> None:
        for data in cycle(self.calls_data):
            logging.info(f'SENT: {data}')
            for client in self.calls_clients:
                await client.send_json(data)
            await asyncio.sleep(2)


async def start_server(app):
    await app['server'].start()


def main(host, port, username, password, dumpfile):
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()

    try:
        app = web.Application(loop=loop)
        server = Server(loop, username, password, dumpfile)
        app['server'] = server

        app.on_startup.append(start_server)
        app.add_routes([web.post('/api/v1/authTokens', server.token)])
        app.add_routes([web.get('/events/v1', server.serve)])
        web.run_app(app, host=host, port=port)

    finally:
        logging.info('Event loop shutdown')
        loop.close()


if __name__ == '__main__':
    main('localhost', 8080, 'username', 'password', 'test/log.json')
