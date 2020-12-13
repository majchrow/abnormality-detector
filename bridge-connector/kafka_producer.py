import asyncio
import json
import logging
from itertools import count
from aiokafka import AIOKafkaProducer

logging.basicConfig(level=logging.INFO)
loop = asyncio.get_event_loop()

async def send(messages):
    producer = AIOKafkaProducer(loop=loop, bootstrap_servers='localhost:9092')
    await producer.start()
    try:
        for i in count():
            for topic, message_list in messages.items():
                l = len(message_list)
                msg = message_list[i % l]
                await producer.send_and_wait(topic, json.dumps(msg).encode())
                await asyncio.sleep(1)
                logging.info(f'pushed {msg}')
    finally:
        await producer.stop()

messages = {
    'preprocessed_callListUpdate': [
        {"call_id": "f53615a1-cfa9-45b8-a62d-a1cd15ac606a", "finished": False, "start_datetime": "2020-12-08 23:30:49.032000+0000", 
            "meeting_name": "[UJ] Biologia (GZ-B)", "last_update": "2020-12-08 23:30:57.403000+0000", "duration": 100},
        {"call_id": "f53615a1-cfa9-45b8-a62d-a1cd15ac606a", "finished": True, "start_datetime": "2020-12-08 23:30:49.032000+0000", 
            "meeting_name": "[UJ] Biologia (GZ-B)", "last_update": "2020-12-08 23:30:57.403000+0000", "duration": 100}
    ],
    'preprocessed_callInfoUpdate': [
        {"call_id": "f53615a1-cfa9-45b8-a62d-a1cd15ac606a", 'datetime': '2020-06-02T00:42:47.984Z', 'time_diff': 123, 'meeting_name': 'Fizyka', 'recording': 1},
        {"call_id": "f53615a1-cfa9-45b8-a62d-a1cd15ac606a", 'datetime': '2020-06-02T00:47:47.984Z', 'time_diff': 123, 'meeting_name': 'Fizyka', 'recording': 1}
    ],
    'preprocessed_rosterUpdate': [
        {'initial': 1, 'connected': 0, 'onhold': 0, 'ringing': 0, 'presenter': 1, 'active_speaker': 1, 'endpoint_recording': 1, 
         'datetime': '2020-06-02T00:46:47.984Z', 'call_id': 'who-cares', 'meeting_name': 'Elektryczność', 'week_day_number': 2, 'hour': 0}
    ],
}

loop.run_until_complete(send(messages))
