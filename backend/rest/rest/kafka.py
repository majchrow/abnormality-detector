import json
from datetime import datetime as dt
from kafka import KafkaConsumer, TopicPartition

from .config import Config


class KafkaConsumerWrapper:
    def __init__(self):
        self.topics = self.consumer = None

    def init(self, bootstrap_server):
        self.topics = ['call-events', 'anomalies-job-status']
        self.consumer = KafkaConsumer(bootstrap_servers=bootstrap_server)
        self.consumer.subscribe(topics=self.topics)

    def get_last(self, num_msg):
        topic_partitions = [
            TopicPartition(t, pt) for t in self.topics for pt in self.consumer.partitions_for_topic(t)
        ]
        end_offsets = self.consumer.end_offsets(topic_partitions)

        # No idea how many messages there are on each partition - fetch max necessary
        fetch_offsets = {
            partition: max(offset - num_msg, 0) for partition, offset in end_offsets.items()
        }
        [self.consumer.seek(partition, offset) for partition, offset in fetch_offsets.items()]
        tp_messages = self.consumer.poll(timeout_ms=100)
        messages = [(tp.topic, record) for tp, records in tp_messages.items() for record in records]
        messages = sorted(messages, key=lambda partition_record: partition_record[1].timestamp)[-num_msg:]

        return [{
            'topic': topic, 
            'timestamp': dt.fromtimestamp(int(record.timestamp / 1000)), 
            'content': json.loads(record.value.decode())
        } for topic, record in messages]


kafka_consumer = KafkaConsumerWrapper()


def setup_kafka(config: Config):
    kafka_consumer.init(config.kafka_bootstrap_server)

