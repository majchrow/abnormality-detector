import os
from dataclasses import dataclass
from typing import Dict


@dataclass
class Config:
    kafka_bootstrap_server = os.environ["KAFKA"]
    kafka_topic_map: Dict[str, str]  # input topic name -> standard CMS message type name

    cassandra_host = os.environ["CASSANDRA_HOST"]
    cassandra_port = os.environ["CASSANDRA_PORT"]
    cassandra_user = os.environ["CASSANDRA_USER"]
    cassandra_passwd = os.environ["CASSANDRA_PASSWD"]
    keyspace = os.environ["KEYSPACE"]
    call_info_table = os.environ["CALL_INFO_TABLE"]
    roster_table = os.environ["ROSTER_TABLE"]
    meetings_table = os.environ["MEETINGS_TABLE"]

    def __post_init__(self):
        assert set(self.kafka_topic_map.values()) == {'callListUpdate', 'callInfoUpdate', 'rosterUpdate'}
