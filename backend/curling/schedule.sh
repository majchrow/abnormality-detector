#!/bin/bash
if [ -z  "$1" ]; then
    echo "Pass conference name as parameter!"
    exit
fi

curl -X PUT -d '{"type": "threshold", "criteria": "whatever!"}' localhost:5001/monitoring/$1
