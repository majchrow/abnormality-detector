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
        self.subscriber_groups = {}

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
                call_event_listeners = self.subscriber_groups.get('call-events', None)
                user_notification_listeners = self.subscriber_groups.get('user-notifications', None)

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

                        if user_notification_listeners:
                            logging.info(f'{self.TAG}: pushing generic info msg to {len(user_notification_listeners)} subscribers')
                            for queue in user_notification_listeners:
                                queue.put_nowait(msg)
                   
                        msg = msg.copy()
                        msg['meeting_name'] = msg.pop('name')
                        msg['datetime'] = msg_dict['last_update']
                        msg['start_datetime'] = msg_dict['start_datetime']

                        if call_event_listeners:
                            logging.info(f'{self.TAG}: pushing call event msg to {len(call_event_listeners)} subscribers')
                            for queue in call_event_listeners:
                                queue.put_nowait(msg)

                        await self.producer.send_and_wait(topic='call-events', value=json.dumps(msg).encode())
                        logging.info(f'{self.TAG}: msg pushed to call-events topic')

                    continue

                if msg.topic == 'anomalies-job-status' and user_notification_listeners:
                    call_name, status, event = msg_dict['meeting_name'], msg_dict['status'], msg_dict['event']
                    msg = {'name': call_name, 'status': status, 'event': event, 'timestamp': timestamp}
                    logging.info(f'{self.TAG}: pushing training job result to {len(user_notification_listeners)} subscribers')
                    for queue in user_notification_listeners:
                        queue.put_nowait(msg)
                    continue

                if not (listeners := self.subscriber_groups.get(f"monitoring-anomalies: {msg_dict['meeting_name']}", None)):
                    continue

                logging.info(f'{self.TAG}: pushing anomaly msg to {len(listeners)} listeners')
                for queue in listeners:
                    queue.put_nowait(msg_dict['anomalies'])
        except Exception as e:
            logging.error(str(e))
            # TODO: restart!
            raise e
        finally:
            await self.consumer.stop()

    def user_notifications_subscribe(self, queue):
        self.subscribe(queue, 'user-notifications')

    def user_notifications_unsubscribe(self, queue):
        self.unsubscribe(queue, 'user-notifications')

    def call_events_subscribe(self, queue):
        self.subscribe(queue, 'call-events')

    def call_events_unsubscribe(self, queue):
        self.unsubscribe(queue, 'call-events')

    def monitoring_subscribe(self, meeting_name, queue):
        self.subscribe(queue, f'monitoring-anomalies: {meeting_name}')

    def monitoring_unsubscribe(self, meeting_name, queue):
        self.unsubscribe(queue, f'monitoring-anomalies: {meeting_name}')

    def subscribe(self, queue, resource: str):
        logging.info(f'{self.TAG}: registered subscriber for {resource}')

        if (sinks := self.subscriber_groups.get(resource, None)) is None:
            sinks = set()
            self.subscriber_groups[resource] = sinks
        sinks.add(queue)

    def unsubscribe(self, queue, resource: str):
        if not (sinks := self.subscriber_groups.get(resource, None)):
            logging.warning(f'{self.TAG}: "unsubscribe" attempt for {resource} that\'s not been subscribed to!')
        else:
            try:
                sinks.remove(queue)
                logging.info(f'{self.TAG}: unregistered subscriber for {resource}')
                if not sinks:
                    del self.subscriber_groups[resource]
            except KeyError:
                logging.warning(f'{self.TAG}: "unsubscribe" attempt for {resource} - not a subscriber!')

