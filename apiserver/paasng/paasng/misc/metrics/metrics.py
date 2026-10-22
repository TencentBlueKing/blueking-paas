# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

# e2b 沙箱对账。outcome 取值见 E2BReconcileOutcome
E2B_SANDBOX_RECONCILED_COUNTER = Counter("e2b_sandbox_reconciled", "", ("cluster", "outcome"))

# 沙箱接口请求总数. operation 取值见 SandboxOperation, result 取值见 SandboxRequestResult
AGENT_SANDBOX_REQUESTS_COUNTER = Counter("agent_sandbox_requests", "", ("app_code", "operation", "result"))

# 沙箱接口请求耗时(秒)
AGENT_SANDBOX_REQUEST_DURATION_HISTOGRAM = Histogram(
    "agent_sandbox_request_duration_seconds",
    "",
    ("operation", "result"),
    buckets=[0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300, 600],
)

# 沙箱就绪耗时(秒). result 取值见 SandboxRequestResult:
# 成功时是 "创建并等到就绪" 的总耗时, 失败时是从开始创建到判定失败的耗时
AGENT_SANDBOX_CREATE_DURATION_HISTOGRAM = Histogram(
    "agent_sandbox_create_duration_seconds",
    "",
    ("workload_type", "cluster", "result"),
    buckets=[1, 2, 5, 10, 30, 60, 120, 180, 300, 420, 600],
)

# 沙箱创建失败原因. reason 取值见 SandboxCreateFailureReason
AGENT_SANDBOX_CREATE_FAILURES_COUNTER = Counter(
    "agent_sandbox_create_failures", "", ("workload_type", "cluster", "reason")
)

# 沙箱存活时长(秒), 按 deleted_at - started_at 计算; delete_source 取值见 SandboxDeleteSource
AGENT_SANDBOX_LIFETIME_HISTOGRAM = Histogram(
    "agent_sandbox_lifetime_seconds",
    "",
    ("workload_type", "delete_source"),
    buckets=[30, 60, 300, 600, 1800, 3600, 7200, 21600, 43200, 86400],
)

# e2b 网关调用. method 是 HTTP 动词, outcome 取值见 E2BGatewayOutcome
E2B_GATEWAY_REQUESTS_COUNTER = Counter("e2b_gateway_requests", "", ("cluster", "method", "outcome"))
