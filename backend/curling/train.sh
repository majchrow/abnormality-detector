#!/bin/bash
curl -X PUT -d '{"calls": ["2020-12-08 23:30:49.032"]}' localhost:5001/anomaly-detection/train/$1
