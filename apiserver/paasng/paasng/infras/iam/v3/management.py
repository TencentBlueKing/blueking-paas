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

from typing import Dict, List

from paasng.infras.iam.base.backends import BaseManagementBackend
from paasng.infras.iam.base.dto import UserGroup
from paasng.infras.iam.client import BKIAMClient
from paasng.infras.iam.permissions.resources.application import AppAction


class BKIAMV3ManagementBackend(BaseManagementBackend):
    """基于 V3 网关接口的权限管理实现

    薄适配层：将版本无关的方法名与 DTO 映射到 `BKIAMClient` 上。V3 语义中的
    「分级管理员」对应契约中的「管理空间」。

    :param operator: V3 的写操作不要求携带操作人，该参数仅为统一两个版本的构造方式而保留
    """

    def __init__(self, tenant_id: str, operator: str | None = None):
        self.tenant_id = tenant_id
        self.operator = operator
        self._client = BKIAMClient(tenant_id)

    # ---------------- 管理空间（V3 语义为分级管理员） ----------------

    def create_management_space(
        self,
        app_code: str,
        app_name: str,
        init_member: str | None = None,
        bk_space_id: str | None = None,
    ) -> int:
        return self._client.create_grade_managers(app_code, app_name, init_member)

    def fetch_management_space(self, app_code: str) -> int:
        return self._client.fetch_grade_manager(app_code)

    def delete_management_space(self, space_id: int):
        return self._client.delete_grade_manager(space_id)

    def fetch_management_space_members(self, space_id: int) -> List[str]:
        return self._client.fetch_grade_manager_members(space_id)

    def add_management_space_members(self, space_id: int, usernames: List[str], operator: str | None = None):
        return self._client.add_grade_manager_members(space_id, usernames)

    def delete_management_space_members(self, space_id: int, usernames: List[str], operator: str | None = None):
        return self._client.delete_grade_manager_members(space_id, usernames)

    def update_management_space_scopes(
        self, space_id: int, app_code: str, app_name: str, bk_space_id: str, operator: str | None = None
    ):
        return self._client.update_grade_managers_with_bksaas_space(space_id, app_code, app_name, bk_space_id)

    # ---------------- 用户组与成员 ----------------

    def create_builtin_user_groups(
        self,
        space_id: int,
        app_code: str,
        app_name: str = "",
        init_members: List[str] | None = None,
    ) -> List[UserGroup]:
        groups = self._client.create_builtin_user_groups(space_id, app_code)
        # app_name / init_members 仅 V4 使用：V3 仍分步授权、加成员
        return [self._to_user_group(group) for group in groups]

    def delete_user_groups(self, user_group_ids: List[int]):
        return self._client.delete_user_groups(user_group_ids)

    def fetch_user_group_members(self, user_group_id: int) -> List[str]:
        return self._client.fetch_user_group_members(user_group_id)

    def add_user_group_members(
        self, user_group_id: int, usernames: List[str], expired_after_days: int, operator: str | None = None
    ):
        return self._client.add_user_group_members(user_group_id, usernames, expired_after_days)

    def delete_user_group_members(self, user_group_id: int, usernames: List[str], operator: str | None = None):
        return self._client.delete_user_group_members(user_group_id, usernames)

    # ---------------- 授权 ----------------

    def grant_user_group_policies(self, app_code: str, app_name: str, groups: List[UserGroup]):
        return self._client.grant_user_group_policies(app_code, app_name, self._to_group_dicts(groups))

    def revoke_user_group_policies(self, user_group_id: int, actions: List[AppAction]):
        return self._client.revoke_user_group_policies(user_group_id, actions)

    def grant_user_group_policies_in_bk_monitor(self, bk_space_id: str, app_name: str, groups: List[UserGroup]):
        return self._client.grant_user_group_policies_in_bk_monitor(
            bk_space_id, app_name, self._to_group_dicts(groups)
        )

    def grant_user_group_policies_in_bk_log(self, bk_space_id: str, app_name: str, groups: List[UserGroup]):
        return self._client.grant_user_group_policies_in_bk_log(bk_space_id, app_name, self._to_group_dicts(groups))

    @staticmethod
    def _to_user_group(group: Dict) -> UserGroup:
        return UserGroup(
            id=group["id"],
            name=group["name"],
            role=int(group["role"]),
            description=group.get("description", ""),
        )

    @staticmethod
    def _to_group_dicts(groups: List[UserGroup]) -> List[Dict]:
        """还原为 BKIAMClient 期望的入参结构"""
        return [{"id": group.id, "name": group.name, "role": group.role} for group in groups]
