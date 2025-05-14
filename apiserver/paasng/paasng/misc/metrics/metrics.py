# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

from prometheus_client import Counter, Histogram

# API
API_VISITED_COUNTER = Counter("api_visited_counter", "", ("method", "endpoint", "status"))
# ms as unit
API_VISITED_TIME_CONSUME_HISTOGRAM = Histogram(
    "api_visited_time_consumed", "", ("method", "endpoint", "status"), buckets=[50, 100, 200, 500, 1000, 2000, 5000]
)

NEW_APP_COUNTER = Counter(
    "new_application",
    "",
    (
        "region",
        "language",
        "source_init_template",
    ),
)

# 部署
DEPLOYMENT_TIME_CONSUME_HISTOGRAM = Histogram(
    "time_consumed_by_deployment",
    "",
    ("kind", "status", "language"),
    buckets=[1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096],
)
DEPLOYMENT_STATUS_COUNTER = Counter(
    "status_counter_of_deployment",
    "",
    (
        "kind",
        "status",
    ),
)
DEPLOYMENT_INFO_COUNTER = Counter("deploy_operation", "", ("source_type", "environment", "status"))

# 增强服务
SERVICE_BIND_COUNTER = Counter("service_bind", "", ("service",))
SERVICE_PROVISION_COUNTER = Counter("service_provision", "", ("environment", "service", "plan"))

# 进程
PROCESS_OPERATE_COUNTER = Counter("process_operate", "", ("environment", "operate_type"))
