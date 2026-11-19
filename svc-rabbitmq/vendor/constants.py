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

from enum import IntEnum, StrEnum


class LinkType(IntEnum):
    empty = 0
    proxy = 1
    inherit = 2


class ClusterSource(StrEnum):
    """实例所在集群的来源，记录在单据上下文中，删除实例时据此定位集群"""

    # 方案配置中的 host / clusters
    PLAN = "plan"
    # 按 cluster_selector 标签从数据库中选择
    DB = "db"


# RabbitMQ stream 插件的默认监听端口。凭证里的字段名是 stream_port，平台注入环境变量时
# 会加上服务名前缀，应用最终看到的是 RABBITMQ_STREAM_PORT
DEFAULT_STREAM_PORT = 5552
