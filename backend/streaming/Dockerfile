FROM python:3.8

WORKDIR /aiohttp

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY streaming src/
COPY setup.py setup.py
RUN pip install -e .

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
ENV TRAINING_JOBS_TABLE="training_jobs"
ENV MODELS_TABLE="models"

ENV THRESHOLD_WORKERS=4
ENV ANOMALY_WORKERS=2
ENV INFERENCE_PERIOD_SECONDS=60

EXPOSE 5000
