#!/bin/bash
curl -X PUT -d '{"calls": ["2020-12-09 07:14:04.657"], "threshold": 0.9, "retrain": {"min_duration": 5, "max_participants": 0}}' localhost:5001/anomaly-detection/train/$1
