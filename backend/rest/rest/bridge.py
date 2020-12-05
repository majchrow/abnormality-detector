import requests
import urllib3
from datetime import datetime, timedelta
from lxml import etree
from flask import current_app
from requests.auth import HTTPBasicAuth

from .config import Config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def child_text(element, tag):
    try:
        return element.xpath(tag)[0].text
    except IndexError:
        return ''


class Client:
    def __init__(self, host, port, username, password):
        self.base_uri = f'https://{host}:{port}/api/v1/'
        self.auth = HTTPBasicAuth(username, password)

    def get_cospaces(self):
        return self.all_pages(self.get_cospaces_page)

    def get_cospaces_page(self, offset=0):
        def mk_cospace(cs):
            return {
                'name': child_text(cs, 'name'),
                'uri': child_text(cs, 'uri'),
                'secondaryUri': child_text(cs, 'secondaryUri'),
            }

        response = requests.get(self.base_uri + f'coSpaces?offset={offset}', auth=self.auth, verify=False)
        response.encoding='utf-8'
        tree = etree.fromstring(response.text)
        return list(map(mk_cospace, tree))

    @staticmethod
    def all_pages(self, call):
        # Note: could be concurrent but performance doesn't matter for now
        all_results = []
        offset = 0
        while page_results := call(offset):
            offset += len(page_results)
            all_results.extend(page_results)
        return all_results


class BridgeDao:
    def __init__(self):
        self.client = None
        self.dao = None

    def init(self, bridge_client, db_dao):
        self.client = bridge_client
        self.dao = db_dao
       
    def update_meetings(self):
        cospaces = self.client.get_cospaces()
        meetings = [
            {'meeting_name': cs['name'], 'meeting_number': cs['secondaryUri']} for cs in cospaces
        ]
        self.dao.add_meetings(meetings)
        return meetings

    def get_meetings(self):
        meetings = self.dao.get_meetings()
        if not meetings['meetings']:
            # DB not seeded
            if self.dao.try_lock('meetings'):
                meetings['meetings'] = self.update_meetings()
        return meetings


dao = BridgeDao()


def setup_bridge_dao(app, config: Config):
    from .db import dao as db_dao

    bridge_client = Client(
        config.bridge_host, config.bridge_port, config.bridge_username, config.bridge_password
    )
    dao.init(bridge_client, db_dao)

    def meetings_update_job():
        with app.app_context():
            meetings = dao.update_meetings()
            current_app.logger.info(f'Updated with {len(meetings)} meetings')

    app.scheduler.add_job(
        func=meetings_update_job, 
        trigger='interval', 
        next_run_time=datetime.now() + timedelta(seconds=10),
        days=config.meetings_update_period_d
    )
