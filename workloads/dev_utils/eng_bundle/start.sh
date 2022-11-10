#!/bin/bash
export STORAGE_ROOT=~/engineng_services

# Create etcd directory beforehand to avoid permission issues
mkdir -p $STORAGE_ROOT/etcd0
chmod 777 $STORAGE_ROOT/etcd0

docker-compose up -d 
