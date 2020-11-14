import json
from time import sleep
from json import dumps
from kafka import KafkaProducer
import os

PRODUCER = KafkaProducer(
    bootstrap_servers=[os.environ["KAFKA"]],
    value_serializer=lambda x: dumps(x).encode("utf-8"),
)
FILEPATH = os.environ["FILEPATH"]


if __name__ == "__main__":
    with open(FILEPATH, "r") as f:
        data = json.load(f)

    for j, i in enumerate(data):
        topic = str(i["message"]["type"])
        PRODUCER.send(topic=topic, value=i)
        print(i)
        sleep(3)