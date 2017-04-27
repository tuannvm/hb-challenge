#!/bin/bash
cd /srv/question1/
docker-compose stop
docker-compose rm -f
docker-compose up -d