import json
from time import sleep
from json import dumps
from kafka import KafkaProducer

CALL = "eee585f7-7558-469c-8550-97671c065bdb"
PRODUCER = KafkaProducer(bootstrap_servers=['localhost:9092'],
                            value_serializer=lambda x:
                            dumps(x).encode('utf-8'))
FILEPATH = f"./resources/all_{CALL}.json"                    



if __name__ == "__main__":
    with open(FILEPATH, 'r') as f:
        data = json.load(f)

    for j,i in enumerate(data):
        topic = str(i['message']['type'])
        PRODUCER.send(topic=topic, value=i)
        print(i)
        sleep(5)