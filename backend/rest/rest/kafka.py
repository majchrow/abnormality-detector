from itertools import chain
from kafka import KafkaConsumer, TopicPartition

from .config import Config


class KafkaConsumerWrapper:
    def __init__(self, bootstrap_server):
        self.topics = [
            'preprocessed_callListUpdate', 'monitoring-results-anomalies', 'anomalies-training'
        ]
        self.consumer = KafkaConsumer(bootstrap_servers=bootstrap_server)
        self.consumer.subscribe(topics=self.topics)

    def get_last(self, num_msg):
        topic_partitions = list(chain(*[
            TopicPartition(t, self.consumer.partitions_for_topic(t)) for t in self.topics
        ]))
        end_offsets = self.consumer.end_offsets(topic_partitions)

        # No idea how many messages there are on each partition
        fetch_offsets = {
            partition: max(offset - num_msg, 0) for partition, offset in end_offsets.items()
        }
        [self.consumer.seek(partition, offset) for partition, offset in fetch_offsets.items()]
        messages = self.consumer.poll()
        messages = sorted(messages, key=lambda m: m.timestamp)[:num_msg]
        return messages


kafka_consumer = None


def setup_kafka(config: Config):
    global kafka_consumer
    kafka_consumer = KafkaConsumerWrapper(config.kafka_bootstrap_server)
