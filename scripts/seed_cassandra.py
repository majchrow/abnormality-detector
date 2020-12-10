from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster
from cassandra.concurrent import execute_concurrent_with_args
from cassandra.query import dict_factory
from datetime import datetime, timedelta
from faker import Faker
from random import randint

USER = 'cassandra'
PASSWORD = 'cassandra'
HOST = 'localhost'
PORT = 9042
KEYSPACE = 'test'

session = None
fake = None


def build_session():
    auth_provider = PlainTextAuthProvider(username=USER, password=PASSWORD)
    cassandra = Cluster([HOST], port=PORT, auth_provider=auth_provider)
    return cassandra.connect(KEYSPACE)

def seed_meetings(count):
    meetings = [(fake.word(), str(randint(10000, 20000))) for _ in range(count)]
    stmt = session.prepare(
        'INSERT INTO meetings(meeting_name, meeting_number) VALUES (?, ?);'
    )
    execute_concurrent_with_args(session, stmt, meetings)
    print(f'-> inserted {meetings}')
    return meetings

def seed_calls(meetings, count):
    calls = []

    for m in meetings:
        start_dt = datetime(2020, 12, randint(10, 20), randint(8, 18), randint(0, 5) * 10, 0)
        for _ in range(count):
            duration = timedelta(minutes=randint(2, 30))
            calls.append((m[0], start_dt, start_dt + duration))
            start_dt += duration + timedelta(minutes=randint(2, 30))
    stmt = session.prepare(
        'INSERT INTO calls(meeting_name, start_datetime, last_update, finished) VALUES (?, ?, ?, true);'
    )
    execute_concurrent_with_args(session, stmt, calls)
    print(f'-> inserted calls')
    return calls

def seed_call_info_roster(calls, length):
    call_info = []
    roster = []

    for meeting, start, end in calls:
        duration = (end - start).total_seconds()
        step = int(duration / length)
        cur_dt = start
        for _ in range(length):
            call_info.append((meeting, cur_dt, randint(0, 10), bool(randint(0,1))))
            roster.append((meeting, cur_dt, randint(0, 10), randint(0, 10)))
            cur_dt += timedelta(seconds=step)
               
    stmt = session.prepare(
        'INSERT INTO call_info_update(meeting_name, datetime, max_participants, recording) VALUES (?, ?, ?, ?);'
    )
    execute_concurrent_with_args(session, stmt, call_info)
    print(f'-> inserted call_info')

    stmt = session.prepare(
        'INSERT INTO roster_update(meeting_name, datetime, active_speaker, onhold) VALUES (?, ?, ?, ?);'
    )
    execute_concurrent_with_args(session, stmt, roster)
    print(f'-> inserted roster')

    return calls
   

def main():
    global fake, session
    session = build_session()

    Faker.seed(42)
    fake = Faker()
    meetings = seed_meetings(3)
    calls = seed_calls(meetings, 3)
    seed_call_info_roster(calls, 10)


if __name__ == '__main__':
    main()


