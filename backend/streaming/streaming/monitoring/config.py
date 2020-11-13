from dataclasses import dataclass
from typing import Dict


@dataclass
class Config:
    kafka_bootstrap_server: str
    kafka_topic_map: Dict[str, str]  # input topic name -> standard CMS message type name

    def __post_init__(self):
        assert set(self.kafka_topic_map.values()) == {'callListUpdate', 'callInfoUpdate', 'rosterUpdate'}
