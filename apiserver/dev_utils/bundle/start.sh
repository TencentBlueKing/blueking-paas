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
source .env

mkdir -p $STORAGE_ROOT
# mysql 5.7 不支持 ARM 架构, 强制指定使用 amd64 镜像
DOCKER_DEFAULT_PLATFORM=linux/amd64 docker-compose up -d
