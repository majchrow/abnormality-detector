#!/bin/bash
docker exec -it abnormality-detector_cassandra_1 cqlsh -u cassandra -p cassandra -k test
