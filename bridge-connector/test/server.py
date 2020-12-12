import aiohttp
import asyncio
import json
import logging
import os
import sys
from aiohttp import web
from argparse import ArgumentParser
from dataclasses import dataclass, field
from itertools import cycle
from pprint import pformat
from typing import Dict, List

# Notes:
#  - acknowledgements and subscriptionUpdates are ignored and not sent at all
#  - if subscribed to "calls", clients get all "calls" events from log in order


@dataclass
class DetailSubscription:
    index: int
    call_id: str


@dataclass
class Client:
    ip_address: str
    ws: web.WebSocketResponse

    # lists of subscription indexes
    calls: List[int] = field(default_factory=list)
    call_info: List[DetailSubscription] = field(default_factory=list)
    roster_info: List[DetailSubscription] = field(default_factory=list)

    def clear(self):
        self.calls = []
        self.call_info = []
        self.roster_info = []


class Server:
    def __init__(self, username: str, password: str, dumpfile: str, msg_interval_s: int, run_forever: bool) -> None:
        self.credentials = (username, password)
        self.dumpfile = dumpfile
        self.msg_interval_s = msg_interval_s
        self.auth_token = 'Token-of-eternal-prosperity'
        self.loop = None

        self.clients: Dict[str, Client] = {}            # IP address -> Client
        self.streams: Dict[str, asyncio.Task] = {}      # IP address -> `stream_log` Task

        self.messages = []
        self._prepare_data(run_forever)

    def _prepare_data(self, run_forever: bool) -> None:
        with open(self.dumpfile) as json_file:
            data = json.load(json_file)

        messages = []
        for message in data:
            # ignore server acknowledgements and subscriptionUpdates in the log
            if 'message' not in message:
                continue
            if message['message']['type'] == 'subscriptionUpdate':
                continue

            messages.append(message)

        if run_forever:
            self.messages = cycle(messages)
        else:
            self.messages = messages

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

        await self.register(request.remote, ws)
        await self.handle_ws(request.remote, ws)
        await self.unregister(request.remote)
        logging.info('WebSocket connection closed')

        return ws

    async def register(self, remote_address, ws) -> None:
        client = Client(remote_address, ws)
        self.clients[remote_address] = client

        logging.info(f"{remote_address} connected.")

    async def handle_ws(self, remote_address, ws):
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                if msg.data == 'close':
                    await ws.close()
                else:
                    msg_dict = json.loads(msg.data)
                    await self.handle_msg(remote_address, msg_dict)
                    logging.info(f"RECV FROM {remote_address}:\n{pformat(msg_dict)}")
            elif msg.type == aiohttp.WSMsgType.ERROR:
                print(f'WebSocket connection closed with exception {ws.exception()}')

    async def handle_msg(self, remote_address, msg_dict):
        if 'message' not in msg_dict:
            # ignore acknowledgements
            return

        client = self.clients[remote_address]
        client.clear()

        msg = msg_dict['message']
        if msg['type'] == "subscribeRequest":
            subscriptions = msg['subscriptions']
            for subscription in subscriptions:
                if subscription['type'] == 'calls':
                    client.calls.append(subscription['index'])
                elif subscription['type'] == "callRoster":
                    sub = DetailSubscription(subscription['index'], subscription['call'])
                    client.roster_info.append(sub)
                elif subscription['type'] == "callInfo":
                    sub = DetailSubscription(subscription['index'], subscription['call'])
                    client.call_info.append(sub)

            # Only start streaming once we have some subscription
            if remote_address not in self.streams:
                self.streams[remote_address] = self.loop.create_task(self.stream_log(client))

    async def stream_log(self, client) -> None:
        try:
            for message in cycle(self.messages):
                if message['message']['type'] == "callListUpdate":
                    for s_ind in client.calls:
                        message['message']['subscriptionIndex'] = s_ind
                        await client.ws.send_json(message)
                elif message['message']['type'] == "callInfoUpdate":
                    call_id = message['message']['callInfo']['call']
                    for subscription in client.call_info:
                        if subscription.call_id == call_id:
                            message['message']['subscriptionIndex'] = subscription.index
                            await client.ws.send_json(message)
                elif message['message']['type'] == "rosterUpdate":
                    for subscription in client.roster_info:
                        if subscription.call_id == message['call']:
                            message['message']['subscriptionIndex'] = subscription.index
                            await client.ws.send_json(message)
                else:
                    logging.error(f'Unhandled message type in provided log file: {pformat(message)}')
                    continue

                logging.info(f'SENT:\n{pformat(message)}')
                await asyncio.sleep(self.msg_interval_s)

        except asyncio.CancelledError:
            logging.info(f'Event stream for {client.ip_address} stopped.')

    async def unregister(self, remote_address) -> None:
        if task := self.streams.get(remote_address, None):
            task.cancel()
            await task
            del self.streams[remote_address]
        del self.clients[remote_address]

        logging.info(f"{remote_address} disconnected.")


async def setup_server(app):
    app['server'].loop = asyncio.get_running_loop()


def main(host, port, username, password, dumpfile, msg_interval_s, run_forever):
    logging.basicConfig(level=logging.DEBUG)

    app = web.Application()
    server = Server(username, password, dumpfile, msg_interval_s, run_forever)
    app['server'] = server

    app.on_startup.append(setup_server)
    app.add_routes([web.post('/api/v1/authTokens', server.token)])
    app.add_routes([web.get('/events/v1', server.serve)])
    web.run_app(app, host=host, port=port)


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--host',
                        type=str,
                        default='localhost',
                        help='host')
    parser.add_argument('--port',
                        type=int,
                        default=8080,
                        help='default file for logging module')
    parser.add_argument('--dumpfile',
                        type=str,
                        default='test/full_log.json',
                        help='JSON file with raw server messages')
    parser.add_argument('--interval_s',
                        type=float,
                        default=1,
                        help='interval between  sent messages [s]')
    parser.add_argument('--forever',
                        type=bool,
                        default=False,
                        help='serve messages in a cycle forever')
    return parser.parse_args()


if __name__ == '__main__':
    try:
        login, password = os.environ["BRIDGE_USERNAME"], os.environ["BRIDGE_PASSWORD"]
    except KeyError:
        print("Required BRIDGE_USERNAME and BRIDGE_PASSWORD environmental variables")
        sys.exit(1)

    args = parse_args()
    main(args.host, args.port, login, password, args.dumpfile, args.interval_s, args.run_forever)
