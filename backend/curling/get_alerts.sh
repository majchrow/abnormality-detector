#!/bin/bash
if [ -z "$1" ]; then
    echo "Pass conference name as parameter!"
    exit
fi

curl -N localhost:5001/notifications/$1?type=threshold
