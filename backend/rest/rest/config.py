import os


class Config:
    host = os.environ["CASSANDRA_HOST"]
    port = os.environ["CASSANDRA_PORT"]
    user = os.environ["CASSANDRA_USER"]
    passwd = os.environ["CASSANDRA_PASSWD"]
    keyspace = os.environ["KEYSPACE"]
    calls_table = os.environ["CALLS_TABLE"]
    call_info_table = os.environ["CALL_INFO_TABLE"]
    roster_table = os.environ["ROSTER_TABLE"]
    meetings_table = os.environ["MEETINGS_TABLE"]
    bridge_host = os.environ['BRIDGE_HOST']
    bridge_port = os.environ['BRIDGE_PORT']
    bridge_username = os.environ['BRIDGE_USER']
    bridge_password = os.environ['BRIDGE_PASSWORD']
