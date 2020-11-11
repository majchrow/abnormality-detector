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

MSG_INTERVAL_S = 2

# Workflow:
#  - client connects -> WebSocket is added to server state
#  - clients subscribes -> we start going over message log in order and send him appropriate messages
#  - appropriate means:
#    - if subscribed to "calls" -> send callListUpdates with ALL his "calls" subscription indexes
#    - to "callInfo" -> send callInfoUpdates with ALL his "callInfo" subscription indexes
#      (IMPORTANT: this means that
#    - same goes for "callRoster"

# Notes:
#  - acknowledgements and subscriptionUpdates are ignored and not sent at all
#  - if subscribed to "calls", clients get all "calls" events from log in order
#  - if subscribed to "callRoster" or "callInfo", clients ALSO get all events
#    from log in order - i.e. for a single subscription to a call X client may
#    receive messages from various real calls
#    - reasons:
#      - ATM this data content doesn't matter so much (it's just a simulation)
#      - it's tough to say from which call an event came - because subscription
#        indexes were not used to differentiate calls when current log was built
#     TODO: should be changed with log from client with proper use of subscriptions


@dataclass
class Client:
    ip_address: str
    ws: web.WebSocketResponse

    # lists of subscription indexes
    calls: List[int] = field(default_factory=list)
    call_info: List[int] = field(default_factory=list)
    roster_info: List[int] = field(default_factory=list)

    def clear(self):
        self.calls = []
        self.call_info = []
        self.roster_info = []


class Server:
    def __init__(self, username: str, password: str, dumpfile: str) -> None:
        self.credentials = (username, password)
        self.dumpfile = dumpfile
        self.auth_token = 'Token-of-eternal-prosperity'
        self.loop = None

        self.clients: Dict[str, Client] = {}            # IP address -> Client
        self.streams: Dict[str, asyncio.Task] = {}      # IP address -> `stream_log` Task

        self.messages = []
        self._prepare_data()

    def _prepare_data(self) -> None:
        with open(self.dumpfile) as json_file:
            data = json.load(json_file)

        for message in data:
            # ignore server acknowledgements and subscriptionUpdates in the log
            if 'message' not in message:
                continue
            if message['message']['type'] == 'subscriptionUpdate':
                continue

            self.messages.append(message)

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

    async def unregister(self, remote_address) -> None:
        if task := self.streams.get(remote_address, None):
            task.cancel()
            await task
            del self.streams[remote_address]
        del self.clients[remote_address]

        logging.info(f"{remote_address} disconnected.")

    async def stream_log(self, client) -> None:
        try:
            for message in cycle(self.messages):
                if message['message']['type'] == "callListUpdate":
                    subscriptions = client.calls
                elif message['message']['type'] == "callInfoUpdate":
                    subscriptions = client.call_info
                elif message['message']['type'] == "rosterUpdate":
                    subscriptions = client.roster_info
                else:
                    logging.error(f'Unhandled message type in provided log file: {pformat(message)}')
                    continue

                # TODO:
                #  when we decide to send data from a single real call to single subscription
                #  instead of mixed (like now) then this is the place to change - we need to
                #  filter subscriptions list based on the message to find ones relevant to
                #  this message (based on call ID maybe? for rosterInfo it's more difficult)

                await asyncio.sleep(MSG_INTERVAL_S)
                for s_ind in subscriptions:
                    message['message']['subscriptionIndex'] = s_ind
                    await client.ws.send_json(message)
                    logging.info(f'SENT:\n{pformat(message)}')
        except asyncio.CancelledError:
            logging.info(f'Event stream for {client.ip_address} stopped.')

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
                    client.roster_info.append(subscription['index'])
                elif subscription['type'] == "callInfo":
                    client.call_info.append(subscription['index'])

            # Only start streaming once we have some subscription
            if remote_address not in self.streams:
                self.streams[remote_address] = self.loop.create_task(self.stream_log(client))


async def setup_server(app):
    app['server'].loop = asyncio.get_running_loop()


def main(host, port, username, password, dumpfile):
    logging.basicConfig(level=logging.DEBUG)

    app = web.Application()
    server = Server(username, password, dumpfile)
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
    return parser.parse_args()


if __name__ == '__main__':
    try:
        login, password = os.environ["BRIDGE_USERNAME"], os.environ["BRIDGE_PASSWORD"]
    except KeyError:
        print("Required BRIDGE_USERNAME and BRIDGE_PASSWORD environmental variables")
        sys.exit(1)

    args = parse_args()
    main(args.host, args.port, login, password, args.dumpfile)
