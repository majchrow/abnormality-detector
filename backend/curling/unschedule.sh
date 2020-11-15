#!/bin/bash
if [ -z "$1" ]; then
    echo "Pass conference name as parameter!"
    exit
fi

curl -X DELETE localhost:5001/monitoring/$1?type=threshold
