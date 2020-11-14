"""Utility script to check what's going on @Kafka."""
from aiokafka import AIOKafkaConsumer
import asyncio
import json

loop = asyncio.get_event_loop()

async def consume():
    consumer = AIOKafkaConsumer(
        'callListUpdate', 'callInfoUpdate', 'rosterUpdate',
        loop=loop, bootstrap_servers='localhost:9092'
    )
    await consumer.start()
    try:
        # Consume messages
        async for msg in consumer:
            msg = json.loads(msg.value)
            print(msg)
    finally:
        await consumer.stop()

loop.run_until_complete(consume())
