FROM python:3.8-slim-buster

WORKDIR /flask

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update -qy && \
    apt-get upgrade -qy && \
    apt-get install wkhtmltopdf -y

COPY rest rest/

ENV CASSANDRA_HOST=cassandra
ENV CASSANDRA_PORT=9042
ENV CASSANDRA_PASSWD=cassandra
ENV CASSANDRA_USER=cassandra
ENV KEYSPACE=test
ENV CALLS_TABLE=calls
ENV CALL_INFO_TABLE=call_info_update
ENV ROSTER_TABLE=roster_update
ENV MEETINGS_TABLE=meetings
ENV BRIDGE_HOST=0.0.0.0
ENV BRIDGE_PORT=443
ENV BRIDGE_USER=username
ENV BRIDGE_PASSWORD=password
ENV MEETINGS_UPDATE_PERIOD_DAYS=1
ENV KAFKA=kafka:29092

ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_APP=rest/app:create_app

EXPOSE 5000
