import os
from dataclasses import dataclass


@dataclass
class Config:
    kafka_bootstrap_server = os.environ["KAFKA"]
    kafka_call_list_topic = 'preprocessed_callListUpdate'
    num_workers = 6

    cassandra_host = os.environ["CASSANDRA_HOST"]
    cassandra_port = os.environ["CASSANDRA_PORT"]
    cassandra_user = os.environ["CASSANDRA_USER"]
    cassandra_passwd = os.environ["CASSANDRA_PASSWD"]
    keyspace = os.environ["KEYSPACE"]
    call_info_table = os.environ["CALL_INFO_TABLE"]
    roster_table = os.environ["ROSTER_TABLE"]
    meetings_table = os.environ["MEETINGS_TABLE"]
