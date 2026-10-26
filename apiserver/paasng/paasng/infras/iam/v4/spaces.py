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

"""管理空间请求体拼装

V4 的 `permission_scope` 以角色 + 资源实例表达可授权范围，对应 V3 分级管理员的
`authorization_scopes`（action 列表 + 资源路径）。
"""

from typing import Dict, List, Sequence

from paasng.infras.iam.constants import (
    BK_LOG_SYSTEM_ID,
    BK_MONITOR_SYSTEM_ID,
    ResourceType,
)
from paasng.infras.iam.permissions.resources.application import AppRole
from paasng.infras.iam.v4.definitions import PAAS_RESOURCE_TYPE_ID

# 监控 / 日志系统的业务运维角色，两端 ID 一致
SPACE_OPERATOR_ROLE_ID = "space_operator"

# 监控的业务运维角色关联空间、APM 应用、RUM 应用、仪表盘四类资源，均以监控空间作为资源范围
BK_MONITOR_SPACE_RELATED_RESOURCE_TYPES = ["space", "apm_application", "rum_application", "grafana_dashboard"]

# 日志的业务运维角色关联空间、采集项、ES 源、索引集四类资源，均以监控空间作为资源范围
BK_LOG_SPACE_RELATED_RESOURCE_TYPES = ["space", "collection", "es_source", "indices"]


def build_subject_scope() -> Dict:
    """人员范围：全员可被授权，与 V3 的 `subject_scopes = [{type: "*", id: "*"}]` 对齐"""
    return {"users": ["*"]}


def build_resource_instances(
    resource_type: str,
    instance_id: str,
    related_resource_type_ids: Sequence[str] | None = None,
) -> List[Dict]:
    """
    :param related_resource_type_ids: 角色关联的资源类型，缺省为实例自身的资源类型
    """
    return [
        {
            "related_resource_type_id": related_type,
            "is_any": False,
            "instances": [{"id": instance_id, "type": resource_type}],
        }
        for related_type in related_resource_type_ids or [resource_type]
    ]


def build_permission_scope(
    role_ids: Sequence[str],
    resource_type: str,
    instance_id: str,
    system_id: str | None = None,
    related_resource_type_ids: Sequence[str] | None = None,
) -> List[Dict]:
    """按角色列表构造 V4 权限范围

    :param system_id: 角色所属系统，跨系统授权时必填；为空时权限中心按本系统的角色处理
    """
    scopes = []
    for role_id in role_ids:
        item: Dict = {
            "id": role_id,
            "resources": build_resource_instances(resource_type, instance_id, related_resource_type_ids),
        }
        if system_id:
            item["system_id"] = system_id
        scopes.append(item)
    return scopes


def build_paas_permission_scope(app_code: str) -> List[Dict]:
    return build_permission_scope(
        [str(role) for role in AppRole],
        PAAS_RESOURCE_TYPE_ID,
        app_code,
    )


def build_monitor_permission_scope(bk_space_id: str) -> List[Dict]:
    """监控空间权限范围：固定写入业务运维角色"""
    return build_permission_scope(
        [SPACE_OPERATOR_ROLE_ID],
        ResourceType.BkMonitorSpace,
        bk_space_id,
        system_id=BK_MONITOR_SYSTEM_ID,
        related_resource_type_ids=BK_MONITOR_SPACE_RELATED_RESOURCE_TYPES,
    )


def build_log_permission_scope(bk_space_id: str) -> List[Dict]:
    """日志空间权限范围：固定写入业务运维角色"""
    return build_permission_scope(
        [SPACE_OPERATOR_ROLE_ID],
        ResourceType.BkMonitorSpace,
        bk_space_id,
        system_id=BK_LOG_SYSTEM_ID,
        related_resource_type_ids=BK_LOG_SPACE_RELATED_RESOURCE_TYPES,
    )


def build_observability_permission_scope(bk_space_id: str) -> List[Dict]:
    """监控、日志两个系统的空间权限范围"""
    return [*build_monitor_permission_scope(bk_space_id), *build_log_permission_scope(bk_space_id)]
