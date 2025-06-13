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

import uuid

from blue_krill.data_types.enum import EnumField, IntStructuredEnum, StrStructuredEnum

# 需要在平台侧完全隐藏的字段名称，用户无法在产品上查看该字段内容，只能通过环境变量查看
SERVICE_SENSITIVE_FIELDS: dict = {}

# 需要在平台侧隐藏展示的字段名称，用户可在产品上点击确认按钮后查看字段内容
# 该配置仅对本地增强服务生效，远程增强服务的设置可参考：
# https://github.com/TencentBlueKing/bkpaas-python-sdk/blob/master/sdks/paas-service/paas_service/models.py#L196
SERVICE_HIDDEN_FIELDS: dict = {"redis": ["REDIS_PASSWORD"]}

# 迁移服务的 plan 占位符
LEGACY_PLAN_ID = uuid.UUID("{00000000-0000-0000-0000-000000000000}")
LEGACY_PLAN_INSTANCE = dict(
    uuid=str(LEGACY_PLAN_ID),
    name="legacy-plan",
    description="迁移服务",
    is_active=True,
    is_eager=True,
    properties=dict(),
)


class Category(IntStructuredEnum):
    """Paas service categories"""

    DATA_STORAGE = 1
    MONITORING_HEALTHY = 2


class ServiceType(StrStructuredEnum):
    LOCAL = "local"
    REMOTE = "remote"


class ServiceBindingType(IntStructuredEnum):
    """Type of service binding relationship"""

    NORMAL = 1
    SHARING = 2


class ServiceBindingPolicyType(StrStructuredEnum):
    """The type of service binding policy"""

    # Use the same value under all conditions
    STATIC = "static"

    # Use different values for different app environments
    ENV_SPECIFIC = "env_specific"


class PrecedencePolicyCondType(StrStructuredEnum):
    """The type of precedence policy condition"""

    # Test if the region is in the given list
    REGION_IN = EnumField("region_in", label="Region.in")

    # Test if the cluster is in the given list
    CLUSTER_IN = EnumField("cluster_in", label="Cluster.in")

    # Always match
    ALWAYS_MATCH = EnumField("always_match", label="AlwaysMatch")


class ServiceAllocationPolicyType(StrStructuredEnum):
    """服务分配策略类型"""

    UNIFORM = EnumField("uniform", label="统一分配")
    RULE_BASED = EnumField("rule_based", label="按规则分配")
