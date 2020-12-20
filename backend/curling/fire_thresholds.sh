#!/bin/bash
curl -X PUT -d '{"start": "2020-12-08 07:29:15.962", "end": "2020-12-08 09:05:39.399", "criteria": [{"parameter": "days", "conditions": [{"day": 3}]}, {"parameter": "time_diff", "conditions": {"min": 6000}}, {"parameter": "active_speaker", "conditions": {"max": 2}}]}' localhost:5001/monitoring/once/$1
