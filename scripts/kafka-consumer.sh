#!/bin/bash
docker exec -it abnormality-detector_kafka_1 kafka-console-consumer.sh --topic $1 --bootstrap-server kafka:29092
