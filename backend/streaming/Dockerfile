FROM python:3.8

WORKDIR /aiohttp

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY streaming src/

ENV KAFKA="kafka:29092"
ENV CASSANDRA_HOST="cassandra"
ENV CASSANDRA_USER="cassandra"
ENV CASSANDRA_PORT="9042"
ENV CASSANDRA_PASSWD="cassandra"
ENV KEYSPACE="test"
ENV MEETINGS_TABLE="meetings"
ENV ANOMALIES_TABLE="anomalies"

EXPOSE 5000
