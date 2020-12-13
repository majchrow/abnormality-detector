#!/bin/bash
if [ -z  "$1" ]; then
    echo "Pass conference name as parameter!"
    exit
fi

curl -X PUT -d '{"type": "threshold", "criteria": [{"parameter": "time_diff", "conditions": {"min": 200}}, {"parameter": "days", "conditions": [{"day": 3}]}]}' localhost:5001/monitoring/$1
