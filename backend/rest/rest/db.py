from cassandra.cluster import Cluster
from cassandra.concurrent import execute_concurrent_with_args
from cassandra.query import dict_factory
from cassandra.auth import PlainTextAuthProvider
import datetime
from .exceptions import NotFoundError

from .config import Config
import pandas as pd


class CassandraDAO:
    def __init__(self):
        self.session = None
        self.calls_table = None
        self.call_info_table = None
        self.roster_table = None
        self.meetings_table = None

    def init(
        self,
        cluster,
        keyspace,
        calls_table,
        call_info_table,
        roster_table,
        meetings_table,
    ):
        self.session = cluster.connect(keyspace, wait_for_all_pools=True)
        self.session.row_factory = dict_factory
        self.calls_table = calls_table
        self.call_info_table = call_info_table
        self.roster_table = roster_table
        self.meetings_table = meetings_table
        self.init_locks()

    def init_locks(self):
        pass

    def get_conferences(self):
        calls = self.session.execute(
            f"SELECT meeting_name as name, finished, start_datetime FROM {self.calls_table}"
        ).all()
        meetings = self.session.execute(f"SELECT * FROM {self.meetings_table}").all()

        current = set()
        recent = set()

        interval = 604800  # one week in seconds
        current_datetime = datetime.datetime.now()

        for call in calls:
            if call["finished"] and self.__is_recent(
                interval, current_datetime, call["start_datetime"]
            ):
                recent.add(call["name"])
            else:
                current.add(call["name"])

        meeting_numbers = {
            meeting["meeting_name"]: meeting["meeting_number"] for meeting in meetings
        }

        monitored = [m for m in meetings if m["monitored"]]
        [m.pop("monitored") for m in meetings]
        current = list(
            map(
                lambda call: {
                    "name": call,
                    "meeting_number": meeting_numbers[call],
                    "criteria": [],
                },
                current,
            )
        )
        recent = list(
            map(
                lambda call: {
                    "name": call,
                    "meeting_number": meeting_numbers[call],
                    "criteria": [],
                },
                recent,
            )
        )

        return {"current": current, "recent": recent, "created": monitored}

    def get_calls(self, meeting_name, start_date, end_date):
        query = (
            f"SELECT start_datetime AS start, last_update, finished "
            f"FROM {self.calls_table} WHERE meeting_name = %s"
        )
        args = [meeting_name]

        if start_date:
            query += " AND last_update >= %s"
            args.append(start_date)
        if end_date:
            query += " AND start_datetime <= %s"
            args.append(end_date)
        query += " ALLOW FILTERING;"

        result = self.session.execute(query, args).all()
        return [
            {"start": c["start"], "end": c["last_update"] if c["finished"] else None}
            for c in result
        ]

    def get_meetings(self):
        result = self.session.execute(
            f"SELECT meeting_name as name, meeting_number FROM {self.meetings_table}"
        ).all()
        return {"meetings": result}

    def add_meetings(self, meetings):
        stmt = self.session.prepare(
            f"INSERT INTO {self.meetings_table} (meeting_name, meeting_number) "
            f"VALUES (?, ?);"
        )
        execute_concurrent_with_args(
            self.session,
            stmt,
            [(m["meeting_name"], m["meeting_number"]) for m in meetings],
        )

    def update_meeting(self, name, criteria):
        self.session.execute(
            f"UPDATE {self.meetings_table} SET criteria=%s "
            f"WHERE meeting_name=%s IF EXISTS;",
            (criteria, name),
        )

    def clear_meeting(self, name):
        self.session.execute(
            f"UPDATE {self.meetings_table} "
            f"SET monitored=false, criteria='[]' "
            f"WHERE meeting_name=%s IF EXISTS;",
            (name,),
        )

    def meeting_details(self, name):
        results = self.session.execute(
            f"SELECT meeting_name AS name, meeting_number, criteria FROM {self.meetings_table} "
            f"WHERE meeting_name = %s "
            f"LIMIT 1",
            (name,),
        )
        meetings = list(results)
        if meetings:
            return meetings[0]
        return {}

    def get_anomalies(self, name, start_date, end_date):
        ci_query = (
            f"SELECT meeting_name, datetime, anomaly_reason FROM {self.call_info_table} "
            f"WHERE meeting_name = %s AND anomaly=true "
        )
        roster_query = (
            f"SELECT meeting_name, datetime, anomaly_reason FROM {self.roster_table} "
            f"WHERE meeting_name = %s AND anomaly=true "
        )
        args = [name]

        if start_date:
            ci_query += " AND datetime >= %s"
            roster_query += " AND datetime >= %s"
            args.append(start_date)
        if end_date:
            ci_query += " AND datetime <= %s"
            roster_query += " AND datetime <= %s"
            args.append(end_date)
        ci_query += " ALLOW FILTERING;"
        roster_query += " ALLOW FILTERING;"

        ci_results = self.session.execute(ci_query, args).all()
        roster_results = self.session.execute(roster_query, args).all()
        return {
            "anomalies": sorted(
                ci_results + roster_results, key=lambda r: r["datetime"]
            )
        }

    # TODO: in case we e.g. want only 1 scheduled task to run in multi-worker setting
    def try_lock(self, resource):
        return True

    @staticmethod
    def __is_recent(interval, current_datetime, call_datetime):
        return (current_datetime - call_datetime).total_seconds() <= interval

    def get_call_info_data(self, name, start_date=None, end_date=None):
        result = pd.DataFrame(
            self.session.execute(
                f"SELECT * FROM {self.call_info_table} WHERE meeting_name='{name}'"
            ).all()
        )
        if result.empty:
            raise NotFoundError
        result = self.__separate_date_and_time(result)

        if start_date and end_date:
            result = self.__filter(result, start_date, end_date)

        if result.empty:
            raise NotFoundError

        return result

    def get_call_info_data_for_meeting(self, name, start_datetime):
        result = self.get_call_info_data(name)
        result = result[result["start_datetime"] == start_datetime]
        if result.empty:
            raise NotFoundError
        return result

    def get_roster_data(self, name, start_date=None, end_date=None):
        result = pd.DataFrame(
            self.session.execute(
                f"SELECT * FROM {self.roster_table} WHERE meeting_name='{name}'"
            ).all()
        )
        if result.empty:
            raise NotFoundError
        result = self.__separate_date_and_time(result)
        if start_date and end_date:
            result = self.__filter(result, start_date, end_date)

        if result.empty:
            raise NotFoundError

        return result

    def get_roster_data_for_meeting(self, name, start_datetime):
        result = self.get_roster_data(name)
        result = result[result["start_datetime"] == start_datetime]
        if result.empty:
            raise NotFoundError
        return result

    def get_calls_data(self, name, start_date=None, end_date=None):
        result = pd.DataFrame(
            self.session.execute(
                f"SELECT * FROM {self.calls_table} WHERE meeting_name='{name}' ALLOW FILTERING"
            ).all()
        )
        if result.empty:
            raise NotFoundError
        result["date"] = result["start_datetime"].apply(lambda d: d.date())
        result["start_time"] = result["start_datetime"].apply(lambda d: d.time())
        result["last_update_time"] = result["last_update"].apply(lambda d: d.time())

        if start_date or end_date:
            self.__filter(result, start_date, end_date)

        if result.empty:
            raise NotFoundError
        return result

    def get_calls_data_for_meeting(self, name, start_datetime):
        result = self.get_calls_data(name)
        result = result[result["start_datetime"] == start_datetime]
        if result.empty:
            raise NotFoundError
        return result

    @staticmethod
    def __separate_date_and_time(df):
        df["date"] = df["datetime"].apply(lambda d: d.date())
        df["time"] = df["datetime"].apply(lambda d: d.time())
        return df

    @staticmethod
    def __filter(df, start_date, end_date):
        if start_date:
            df = df[df["date"] >= start_date]
        if end_date:
            df = df[["date"] <= end_date]
        return df


dao = CassandraDAO()


def setup_db(config: Config):
    auth_provider = PlainTextAuthProvider(username=config.user, password=config.passwd)
    cassandra = Cluster([config.host], port=config.port, auth_provider=auth_provider)
    dao.init(
        cassandra,
        config.keyspace,
        config.calls_table,
        config.call_info_table,
        config.roster_table,
        config.meetings_table,
    )
