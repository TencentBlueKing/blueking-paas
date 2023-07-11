#!/bin/bash
##
## TencentBlueKing is pleased to support the open source community by making
## 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
## Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
## Licensed under the MIT License (the "License"); you may not use this file except
## in compliance with the License. You may obtain a copy of the License at
##
##     http://opensource.org/licenses/MIT
##
## Unless required by applicable law or agreed to in writing, software distributed under
## the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
## either express or implied. See the License for the specific language governing permissions and
## limitations under the License.
##
## We undertake not to change the open source license (MIT license) applicable
## to the current version of the project delivered to anyone in the future.
##

K8S_VERSION=$1
current_script_path=$(dirname "$0")

if [[ "$K8S_VERSION" == 1.14* ]]; then
    KIND_EXPERIMENTAL_DOCKER_NETWORK=${NETWORK_NAME:-apiserver-unittest} kind create cluster --name ${KIND_CLUSTER_NAME:-foo114} --image "kindest/node:v1.14.10" --config ${current_script_path}/kind-configs/114.yaml
fi

if [[ "$K8S_VERSION" == 1.16* ]]; then
    KIND_EXPERIMENTAL_DOCKER_NETWORK=${NETWORK_NAME:-apiserver-unittest} kind create cluster --name ${KIND_CLUSTER_NAME:-foo116} --image "kindest/node:v1.16.15" --config ${current_script_path}/kind-configs/116.yaml
fi

if [[ "$K8S_VERSION" == 1.18* ]]; then
    KIND_EXPERIMENTAL_DOCKER_NETWORK=${NETWORK_NAME:-apiserver-unittest} kind create cluster --name ${KIND_CLUSTER_NAME:-foo118} --image "kindest/node:v1.18.20" --config ${current_script_path}/kind-configs/118.yaml
fi

if [[ "$K8S_VERSION" == 1.20* ]]; then
    KIND_EXPERIMENTAL_DOCKER_NETWORK=${NETWORK_NAME:-apiserver-unittest} kind create cluster --name ${KIND_CLUSTER_NAME:-foo120} --image "kindest/node:v1.20.15" --config ${current_script_path}/kind-configs/120.yaml
fi

if [[ "$K8S_VERSION" == 1.22* ]]; then
    KIND_EXPERIMENTAL_DOCKER_NETWORK=${NETWORK_NAME:-apiserver-unittest} kind create cluster --name ${KIND_CLUSTER_NAME:-foo122} --image "kindest/node:v1.22.9" --config ${current_script_path}/kind-configs/122.yaml
fi