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

from typing import Dict, List, Optional

from django.db.models import Q

from paasng.infras.iam.base.backends import BaseAuthBackend
from paasng.infras.iam.base.dto import ActionRequest, AuthResource
from paasng.infras.iam.shim import get_auth_backend


class IAMClient:
    """鉴权入口

    版本无关的门面：按部署环境的配置将调用分发到 V3 或 V4 的实现，调用方无需感知版本差异。
    """

    def _get_auth_backend(self) -> BaseAuthBackend:
        """获取当前环境的鉴权实现，子类可覆盖以注入替身"""
        return get_auth_backend()

    def resource_type_allowed(self, username: str, tenant_id: str, action_id: str, use_cache: bool = False) -> bool:
        """
        判断用户是否具备某个操作的权限
        note: 权限判断与资源实例无关，如创建某资源
        """
        return self._get_auth_backend().resource_type_allowed(username, tenant_id, action_id, use_cache)

    def resource_inst_allowed(
        self, username: str, tenant_id: str, action_id: str, resources: List[AuthResource], use_cache: bool = False
    ) -> bool:
        """
        判断用户对某个资源实例是否具有指定操作的权限
        note: 权限判断与资源实例有关，如更新某个具体资源
        """
        return self._get_auth_backend().resource_inst_allowed(username, tenant_id, action_id, resources, use_cache)

    def resource_inst_multi_actions_allowed(
        self, username: str, tenant_id: str, action_ids: List[str], resources: List[AuthResource]
    ) -> Dict[str, bool]:
        """
        判断用户对某个(单个)资源实例是否具有多个操作的权限.
        note: 权限判断与资源实例有关，如更新某个具体资源

        :returns: 示例 {'view_basic_info': True, 'edit_basic_info': False}
        """
        return self._get_auth_backend().resource_inst_multi_actions_allowed(username, tenant_id, action_ids, resources)

    def batch_resource_multi_actions_allowed(
        self, username: str, tenant_id: str, action_ids: List[str], resources: List[AuthResource]
    ) -> Dict[str, Dict[str, bool]]:
        """
        判断用户对某些资源是否具有多个指定操作的权限. 当前仅支持同类型的资源

        :returns: 示例 {'app_code_test': {'view_basic_info': True, 'edit_basic_info': False}}
        """
        return self._get_auth_backend().batch_resource_multi_actions_allowed(
            username, tenant_id, action_ids, resources
        )

    def build_resource_filter(
        self, username: str, tenant_id: str, action_id: str, key_mapping: Optional[Dict[str, str]] = None
    ) -> Optional[Q]:
        """
        将用户在某操作上的权限策略下推为 Django ORM 过滤条件

        :returns: 过滤条件；None 表示未能取得策略，调用方需按无权限处理
        """
        return self._get_auth_backend().build_resource_filter(username, tenant_id, action_id, key_mapping)

    def build_apply_url(self, tenant_id: str, action_requests: List[ActionRequest]) -> str:
        """生成无权限时的申请链接"""
        return self._get_auth_backend().build_apply_url(tenant_id, action_requests)
