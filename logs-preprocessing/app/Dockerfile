FROM python:3.8

RUN apt-get update && \
    apt-get install -y openjdk-11-jre-headless && \
    apt-get clean;

COPY ./requirements.txt /app/

RUN pip install -r /app/requirements.txt

COPY . /app

WORKDIR /app/

ARG FILEPATH=./main/resources/callInfo_sample.json
ENV FILEPATH="${FILEPATH}"

ARG UPDATE_TYPE=callInfo
ENV UPDATE_TYPE="${UPDATE_TYPE}"

ENV KEYSPACE="test"

ARG TABLE=call_info_update
ENV TABLE="${TABLE}"

ENV KAFKA="kafka:29092"

ENV CASSANDRA_HOST="cassandra"

ENV CASSANDRA_USER="cassandra"

ENV CASSANDRA_PORT="9042"

ENV CASSANDRA_PASSWORD="cassandra"

ARG OUTPUT_MODE=complete
ENV OUTPUT_MODE="${OUTPUT_MODE}"

ARG CORES=*
ENV CORES="${CORES}"

ENV PATH=$PATH:/app/main/src
ENV PYTHONPATH=/app/main/src

CMD ["python3", "./main/src/run.py"]
