from cassandra.cluster import Cluster
from cassandra.query import dict_factory
from cassandra.auth import PlainTextAuthProvider
import datetime


class CassandraDAO:
    def __init__(self):
        self.session = None
        self.calls_table = None
        self.meetings_table = None

    def init(self, cluster, keyspace, calls_table, meetings_table):
        self.session = cluster.connect(keyspace, wait_for_all_pools=True)
        self.session.row_factory = dict_factory
        self.calls_table = calls_table
        self.meetings_table = meetings_table

    def get_conferences(self):
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

        current = self.__transform(lambda call: call[0], current)
        recent = self.__transform(lambda call: call[0], recent)

        created = self.session.execute(f"SELECT meeting_name AS name, criteria FROM {self.meetings_table}").all()
        return {"current": current, "recent": recent, "created": created}

    def update_meeting(self, name, criteria):
        self.session.execute(f"INSERT INTO {self.meetings_table} (meeting_name, criteria) "
                             f"VALUES (%s, %s);", (name, criteria))

    def remove_meeting(self, name):
        self.session.execute(f"DELETE FROM {self.meetings_table} WHERE meeting_name=%s", (name,))

    def meeting_details(self, name):
        results = self.session.execute(f"SELECT meeting_name AS name, criteria FROM {self.meetings_table} "
                                       f"WHERE meeting_name = %s "
                                       f"LIMIT 1", (name,))
        meetings = list(results)
        if meetings:
            return meetings[0]
        return {}

    # Oldies

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
