import os


class Config:
    host = os.environ["CASSANDRA_HOST"]
    port = os.environ["CASSANDRA_PORT"]
    user = os.environ["CASSANDRA_USER"]
    passwd = os.environ["CASSANDRA_PASSWD"]
    keyspace = os.environ["KEYSPACE"]
    calls_table = os.environ["CALLS_TABLE"]
    anomalies_table = os.environ["ANOMALIES_TABLE"]
    meetings_table = os.environ["MEETINGS_TABLE"]
