import os
from dataclasses import dataclass


@dataclass
class Config:
    kafka_bootstrap_server: str = os.environ["KAFKA"]
    kafka_call_list_topic: str = os.environ['CALL_LIST_TOPIC']
    num_threshold_workers: int = int(os.environ['THRESHOLD_WORKERS'])
    num_anomaly_workers: int = int(os.environ['ANOMALY_WORKERS'])

    cassandra_host: str = os.environ["CASSANDRA_HOST"]
    cassandra_port: str = os.environ["CASSANDRA_PORT"]
    cassandra_user: str = os.environ["CASSANDRA_USER"]
    cassandra_passwd: str = os.environ["CASSANDRA_PASSWD"]
    keyspace: str = os.environ["KEYSPACE"]
    call_info_table: str = os.environ["CALL_INFO_TABLE"]
    roster_table: str = os.environ["ROSTER_TABLE"]
    meetings_table: str = os.environ["MEETINGS_TABLE"]
    training_jobs_table: str = os.environ["TRAINING_JOBS_TABLE"]
    models_table: str = os.environ["MODELS_TABLE"]
