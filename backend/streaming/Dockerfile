FROM python:3.8

WORKDIR /aiohttp

COPY streaming src/
COPY setup.py setup.py
COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

ENV KAFKA="kafka:29092"
ENV CALL_LIST_TOPIC="preprocessed_callListUpdate"
ENV CASSANDRA_HOST="cassandra"
ENV CASSANDRA_USER="cassandra"
ENV CASSANDRA_PORT="9042"
ENV CASSANDRA_PASSWD="cassandra"
ENV KEYSPACE="test"
ENV CALL_INFO_TABLE="call_info_update"
ENV ROSTER_TABLE="roster_update"
ENV MEETINGS_TABLE="meetings"
ENV THRESHOLD_WORKERS=4

EXPOSE 5000
