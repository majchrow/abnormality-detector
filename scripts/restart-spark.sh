#!/bin/bash
docker-compose -f docker-compose-dev.yml up -d --force-recreate --build preprocessing-calls preprocessing-roster preprocessing-info
