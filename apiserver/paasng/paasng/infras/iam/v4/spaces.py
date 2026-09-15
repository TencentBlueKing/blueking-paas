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

from typing import Dict, List, Optional, Sequence

from paasng.infras.iam.constants import (
    BK_LOG_SYSTEM_ID,
    BK_MONITOR_SYSTEM_ID,
    ResourceType,
)
from paasng.infras.iam.permissions.resources.application import AppRole
from paasng.infras.iam.v4.definitions import PAAS_RESOURCE_TYPE_ID

# 监控 / 日志系统的业务运维角色，两端 ID 一致
SPACE_OPERATOR_ROLE_ID = "space_operator"


def build_subject_scope() -> Dict:
    """人员范围：全员可被授权，与 V3 的 `subject_scopes = [{type: "*", id: "*"}]` 对齐"""
    return {"users": ["*"]}


def build_resource_instances(resource_type: str, instance_id: str) -> List[Dict]:
    return [
        {
            "related_resource_type_id": resource_type,
            "is_any": False,
            "instances": [{"id": instance_id, "type": resource_type}],
        }
    ]


def build_permission_scope(
    role_ids: Sequence[str],
    resource_type: str,
    instance_id: str,
    system_id: Optional[str] = None,
) -> List[Dict]:
    """按角色列表构造 V4 权限范围

    :param system_id: 跨系统范围时写入目标系统 ID，便于请求体中区分三个系统
    """
    scopes = []
    for role_id in role_ids:
        item: Dict = {
            "id": role_id,
            "resources": build_resource_instances(resource_type, instance_id),
        }
        if system_id:
            item["system"] = system_id
        scopes.append(item)
    return scopes


def build_paas_permission_scope(app_code: str, system_id: str) -> List[Dict]:
    return build_permission_scope(
        [str(role) for role in AppRole],
        PAAS_RESOURCE_TYPE_ID,
        app_code,
        system_id=system_id,
    )


def build_monitor_permission_scope(bk_space_id: str) -> List[Dict]:
    """监控空间权限范围：固定写入业务运维角色"""
    return build_permission_scope(
        [SPACE_OPERATOR_ROLE_ID],
        ResourceType.BkMonitorSpace,
        bk_space_id,
        system_id=BK_MONITOR_SYSTEM_ID,
    )


def build_log_permission_scope(bk_space_id: str) -> List[Dict]:
    """日志空间权限范围：固定写入业务运维角色"""
    return build_permission_scope(
        [SPACE_OPERATOR_ROLE_ID],
        ResourceType.BkMonitorSpace,
        bk_space_id,
        system_id=BK_LOG_SYSTEM_ID,
    )
