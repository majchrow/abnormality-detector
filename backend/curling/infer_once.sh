#!/bin/bash
curl -X PUT -d '{"start": "2020-12-08 11:49:08.478", "end": "2020-12-08 23:28:55.538"}' localhost:5001/anomaly-detection/inference/$1
