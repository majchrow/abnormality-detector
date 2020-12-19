#!/bin/bash
curl -X PUT -d '{"training_calls": ["2020-12-07 18:52:14.136"], "start": "2020-12-08 07:29:15.962", "end": "2020-12-08 09:05:39.399", "threshold": 0.9}' localhost:5001/anomaly-detection/once/$1
