#!/bin/bash
docker-compose -f docker-compose-dev.yml up -d --force-recreate test-producer
sleep 5
docker-compose -f docker-compose-dev.yml up -d --force-recreate bridge-connector
