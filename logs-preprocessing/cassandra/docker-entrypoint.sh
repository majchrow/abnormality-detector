#!/bin/bash
if [[ ! -z "$CASSANDRA_KEYSPACE" && $1 = 'cassandra' ]]; then
    CQL="CREATE KEYSPACE $CASSANDRA_KEYSPACE WITH REPLICATION = {'class': 'SimpleStrategy', 'replication_factor': 1}; USE $CASSANDRA_KEYSPACE; CREATE TABLE $TABLE(id text PRIMARY KEY, date text, call_id text, initial text, ringing text, connected text, onhold text, activespeaker text, presenter text, endpointrecording text);"
    until echo $CQL | cqlsh; do
        echo "cqlsh: Cassandra is unavailable - retry later"
        sleep 2
    done &
fi
