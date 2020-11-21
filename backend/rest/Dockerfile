FROM python:3.8

WORKDIR /flask

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY rest rest/

ENV CASSANDRA_HOST=cassandra
ENV CASSANDRA_PORT=9042
ENV CASSANDRA_PASSWD=cassandra
ENV CASSANDRA_USER=cassandra
ENV KEYSPACE=test
ENV CALLS_TABLE=calls
ENV ANOMALIES_TABLE="anomalies"
ENV MEETINGS_TABLE=meetings

ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_APP=rest/app:create_app

EXPOSE 5000
