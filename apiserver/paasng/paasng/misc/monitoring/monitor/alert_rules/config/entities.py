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

from blue_krill.data_types.enum import StrStructuredEnum


class AlertCode(StrStructuredEnum):
    HIGH_CPU_USAGE = "high_cpu_usage"
    HIGH_MEM_USAGE = "high_mem_usage"
    POD_RESTART = "pod_restart"
    OOM_KILLED = "oom_killed"
    # 队列消息数超过阈值时触发
    HIGH_RABBITMQ_QUEUE_MESSAGES = "high_rabbitmq_queue_messages"
    # 死信队列(DLX)消息数超过阈值时触发
    HIGH_RABBITMQ_DLX_QUEUE_MESSAGES = "high_rabbitmq_dlx_queue_messages"
    # 队列数使用率(queues/limits)超过阈值时触发
    HIGH_RABBITMQ_QUEUES_USAGE = "high_rabbitmq_queues_usage"
    # 连接数使用率(connections/limits)超过阈值时触发
    HIGH_RABBITMQ_CONNECTIONS_USAGE = "high_rabbitmq_connections_usage"
    # 队列消息使用率(queue_usage)超过阈值时触发
    HIGH_RABBITMQ_QUEUE_USAGE = "high_rabbitmq_queue_usage"
    GCS_MYSQL_SLOW_QUERY = "gcs_mysql_slow_query"
    HIGH_BKREPO_QUOTA_USAGE = "high_bkrepo_quota_usage"
