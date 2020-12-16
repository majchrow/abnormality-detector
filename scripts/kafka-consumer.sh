#!/bin/bash
docker exec -it abnormality-detector_kafka_1 bash -c "unset KAFKA_OPTS; kafka-console-consumer.sh --topic $1 --bootstrap-server kafka:29092"
