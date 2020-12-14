#!/bin/bash
docker-compose -f docker-compose-dev.yml rm -sfv cassandra
docker volume rm abnormality-detector_cassandra_data
docker-compose -f docker-compose-dev.yml up -d cassandra
sleep 80
docker-compose -f docker-compose-dev.yml up cassandra-load-keyspace
