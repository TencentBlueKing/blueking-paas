#!/bin/bash
source .env

mkdir -p $STORAGE_ROOT
docker-compose up -d --remove-orphan
