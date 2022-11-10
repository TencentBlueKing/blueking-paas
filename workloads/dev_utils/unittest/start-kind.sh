#!/bin/bash

K8S_VERSION=$1

if [[ "$K8S_VERSION" == 1.14* ]]; then
    KIND_EXPERIMENTAL_DOCKER_NETWORK=${NETWORK_NAME:-engine-unittest} kind create cluster --name ${KIND_CLUSTER_NAME:-foo114} --image "kindest/node:v1.14.10" --config kind-configs/114.yaml
fi

if [[ "$K8S_VERSION" == 1.16* ]]; then
    KIND_EXPERIMENTAL_DOCKER_NETWORK=${NETWORK_NAME:-engine-unittest} kind create cluster --name ${KIND_CLUSTER_NAME:-foo116} --image "kindest/node:v1.16.15" --config kind-configs/116.yaml
fi

if [[ "$K8S_VERSION" == 1.18* ]]; then
    KIND_EXPERIMENTAL_DOCKER_NETWORK=${NETWORK_NAME:-engine-unittest} kind create cluster --name ${KIND_CLUSTER_NAME:-foo118} --image "kindest/node:v1.18.20" --config kind-configs/118.yaml
fi

if [[ "$K8S_VERSION" == 1.20* ]]; then
    KIND_EXPERIMENTAL_DOCKER_NETWORK=${NETWORK_NAME:-engine-unittest} kind create cluster --name ${KIND_CLUSTER_NAME:-foo120} --image "kindest/node:v1.20.15" --config kind-configs/120.yaml
fi

if [[ "$K8S_VERSION" == 1.22* ]]; then
    KIND_EXPERIMENTAL_DOCKER_NETWORK=${NETWORK_NAME:-engine-unittest} kind create cluster --name ${KIND_CLUSTER_NAME:-foo122} --image "kindest/node:v1.22.9" --config kind-configs/122.yaml
fi
