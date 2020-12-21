import json
import logging
import pytz
from aiokafka import AIOKafkaConsumer
from datetime import datetime as dt, timezone


class KafkaEndpoint:

    TAG = 'KafkaEndpoint'

    def __init__(self, bootstrap_server, call_list_topic):
        self.bootstrap_server = bootstrap_server
        self.call_list_topic = call_list_topic
        self.call_event_listeners = set()
        self.anomaly_listeners = {}

        self.consumer = None
        self.producer = None

    def init(self, kafka_producer):
        self.producer = kafka_producer

    async def run(self):
        self.consumer = AIOKafkaConsumer(
            self.call_list_topic, 'monitoring-results-anomalies', 'anomalies-job-status', bootstrap_servers='kafka:29092',
        )
        await self.consumer.start()

        try:
            async for msg in self.consumer:               
                msg_dict = json.loads(msg.value.decode())
                timestamp = dt.fromtimestamp(int(msg.timestamp / 1000)).replace(tzinfo=timezone.utc).astimezone(tz=pytz.timezone('Europe/Warsaw')).isoformat()

                if msg.topic == self.call_list_topic:
                    call_name = msg_dict['meeting_name']
                    if msg_dict['finished']:
                        event = 'Meeting finished'
                    elif msg_dict['start_datetime'] == msg_dict['last_update']:
                        event = 'Meeting started'
                    else:
                        event = None
                    if event:
                        msg = {'name': call_name, 'status': 'info', 'event': event, 'timestamp': timestamp}

                        if self.call_event_listeners:
                            logging.info(f'{self.TAG}: pushing call info {msg} to {len(self.call_event_listeners)} subscribers')
                            for queue in self.call_event_listeners:
                                queue.put_nowait(msg)
                   
                        msg = msg.copy()
                        msg['meeting_name'] = msg.pop('name')
                        msg['datetime'] = msg_dict['last_update']
                        msg['start_datetime'] = msg_dict['start_datetime']
                        await self.producer.send_and_wait(topic='call-events', value=json.dumps(msg).encode())
                        logging.info(f'{self.TAG}: pushed {msg} to call-events topic')

                    continue

                if msg.topic == 'anomalies-job-status' and self.call_event_listeners:
                    call_name, status, event = msg_dict['meeting_name'], msg_dict['status'], msg_dict['event']
                    msg = {'name': call_name, 'status': status, 'event': event, 'timestamp': timestamp}
                    logging.info(f'{self.TAG}: pushing training job result {msg} to {len(self.call_event_listeners)} subscribers')
                    for queue in self.call_event_listeners:
                        queue.put_nowait(msg)
                    continue

                if not (listeners := self.anomaly_listeners.get(msg_dict['meeting'], None)):
                    continue

                logging.info(f'{self.TAG}: pushing {msg_dict} to {len(listeners)} listeners')
                for queue in listeners:
                    queue.put_nowait(msg_dict['anomalies'])
        except:
            raise
        finally:
            await self.consumer.stop()

    def call_event_subscribe(self, queue):
        logging.info(f'{self.TAG}: registered call event subscriber')
        self.call_event_listeners.add(queue)

    def call_event_unsubscribe(self, queue):
        if queue in self.call_event_listeners:
            self.call_event_listeners.remove(queue)
            logging.info(f'{self.TAG}: unregistered call event subscriber')
        else:
            logging.info(f'{self.TAG}: "unsubscribe call events" attempt - subscriber not found')

    def monitoring_subscribe(self, conf_name: str, queue):
        logging.info(f'{self.TAG}: registered subscriber for {conf_name}')

        if (sinks := self.anomaly_listeners.get(conf_name, None)) is None:
            sinks = set()
            self.anomaly_listeners[conf_name] = sinks
        sinks.add(queue)

    def monitoring_unsubscribe(self, conf_name: str, queue):
        if not (sinks := self.anomaly_listeners.get(conf_name, None)):
            logging.warning(f'{self.TAG}: "unsubscribe" attempt for {conf_name} - conference unmonitored!')
        else:
            try:
                sinks.remove(queue)
                logging.info(f'{self.TAG}: unregistered subscriber for {conf_name}')
                if not sinks:
                    del self.anomaly_listeners[conf_name]
            except KeyError:
                logging.warning(f'{self.TAG}: "unsubscribe" attempt for {conf_name} - not a subscriber!')
