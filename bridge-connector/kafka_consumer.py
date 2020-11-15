"""Utility script to check what's going on @Kafka."""
from aiokafka import AIOKafkaConsumer
import asyncio
import json

import logging
logging.basicConfig(level=logging.INFO)

loop = asyncio.get_event_loop()

async def consume():
    consumer = AIOKafkaConsumer(
        'preprocessed_callListUpdate', 'preprocessed_callInfoUpdate', 'preprocessed_rosterUpdate',
        loop=loop, bootstrap_servers='localhost:9092'
    )
    await consumer.start()
    try:
        # Consume messages
        async for msg in consumer:
            msg = json.loads(msg.value)
            logging.info(msg)
    finally:
        await consumer.stop()

loop.run_until_complete(consume())
