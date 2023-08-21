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

current_script_path=$(dirname "$0")
K8S_VERSION=$1


function create_cluster() {
    local version=$1
    local image=$2
    local config=$3
    # 使用 kind 创建 集群
    KIND_EXPERIMENTAL_DOCKER_NETWORK=${NETWORK_NAME:-apiserver-unittest} kind create cluster --name ${KIND_CLUSTER_NAME:-foo${version}} --image "$image" --config "${current_script_path}/kind-configs/${config}.yaml"
    # 加载集成测试需要的镜像
    kind load docker-image busybox:latest --name ${KIND_CLUSTER_NAME:-foo${version}}
    kind load docker-image ealen/echo-server:0.7.0 --name ${KIND_CLUSTER_NAME:-foo${version}}
}


if [[ "$K8S_VERSION" == 1.14* ]]; then
    create_cluster "114" "kindest/node:v1.14.10" "114"
elif [[ "$K8S_VERSION" == 1.16* ]]; then
    create_cluster "116" "kindest/node:v1.16.15" "116"
elif [[ "$K8S_VERSION" == 1.18* ]]; then
    create_cluster "118" "kindest/node:v1.18.20" "118"
elif [[ "$K8S_VERSION" == 1.20* ]]; then
    create_cluster "120" "kindest/node:v1.20.15" "120"
elif [[ "$K8S_VERSION" == 1.22* ]]; then
    create_cluster "122" "kindest/node:v1.22.9" "122"
else
    echo "Invalid K8S_VERSION: $K8S_VERSION"
    echo "Supported versions: 1.14, 1.16, 1.18, 1.20, 1.22"
    exit 1
fi
