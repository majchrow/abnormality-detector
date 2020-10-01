import json
from time import sleep
from json import dumps
from kafka import KafkaProducer

f = open('mix.json', )
data = json.load(f)



producer = KafkaProducer(bootstrap_servers=['localhost:9092'],
                         value_serializer=lambda x:
                         dumps(x).encode('utf-8'))


for i in data:
    topic = str(i['message']['type'])
    producer.send(topic=topic, value=i)
    print(i)
    sleep(2)


