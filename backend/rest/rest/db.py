import logging
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
import datetime


class CassandraDAO:
    def __init__(self):
        self.session = None
        self.calls_table = None
        self.meetings_table = None

    def init(self, cluster, keyspace, calls_table, meetings_table):
        self.session = cluster.connect(keyspace, wait_for_all_pools=True)
        self.calls_table = calls_table
        self.meetings_table = meetings_table

    def get_conferences(self):
        return {"current": [], "recent": [], "future": []}

        result = self.session.execute(f"SELECT * FROM {self.calls_table}").all()

        calls = self.__transform(
            lambda call: (
                {"id": call.call_id, "name": call.name},
                call.finished,
                call.start_datetime,
            ),
            result,
        )

        current = []
        recent = []

        interval = 604800  # one week in seconds
        current_datetime = datetime.datetime.now()

        for call in calls:
            if call[1] and self.__check_if_recent(interval, current_datetime, call[2]):
                recent.append(call)
            else:
                current.append(call)

        self.future = self.future.difference(
            set(self.__transform(lambda call: call[0]["name"], current))
        )
        future = self.__transform(
            lambda call: {"id": -1, "name": call}, list(self.future)
        )

        current = self.__transform(lambda call: call[0], current)
        recent = self.__transform(lambda call: call[0], recent)

        return {"current": current, "recent": recent, "future": future}

    def add_meeting(self, name, criteria):
        logging.info(f'{name}, {criteria}')
        return
        self.meetings[name] = criteria

    def update_meeting(self, name, criteria):
        logging.info(f'{name}, {criteria}')

        return
        self.meetings[name] = criteria

    def remove_meeting(self, name):
        logging.info(f'{name}')
        return
        del self.meetings[name]

    # Oldies

    def add_to_future(self, name):
        self.future.add(name)

    def is_in_future(self, name):
        return name in self.future

    def remove_from_future(self, name):
        if name in self.future:
            self.future.remove(name)

    def conference_details(self, conf_id):
        result = self.session.execute(
            f"SELECT * FROM {self.calls_table} WHERE call_id='{conf_id}'"
        )
        calls = result.all()
        call = calls[0] if calls else None

        return (
            self.__create_conf_details_dict(
                call.call_id, call.name, str(call.start_datetime)
            )
            if call
            else self.__create_conf_details_dict(conf_id, "unknown", "unknown")
        )

    @staticmethod
    def __create_conf_details_dict(call_id, call_name, start_datetime):
        return {"id": call_id, "name": call_name, "start_time": start_datetime}

    @staticmethod
    def __transform(transformation, data):
        return list(map(transformation, data))

    @staticmethod
    def __check_if_recent(interval, current_datetime, call_datetime):
        return (current_datetime - call_datetime).total_seconds() <= interval


dao = CassandraDAO()


def setup_db(host, port, user, passwd, keyspace, calls_table, meetings_table):
    auth_provider = PlainTextAuthProvider(username=user, password=passwd)
    cassandra = Cluster([host], port=port, auth_provider=auth_provider)
    dao.init(cassandra, keyspace, calls_table, meetings_table)
