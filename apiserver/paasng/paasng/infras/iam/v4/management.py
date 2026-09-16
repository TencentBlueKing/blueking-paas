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

import logging
from http import HTTPStatus
from typing import Dict, Iterable, List, Sequence

from paasng.infras.iam import utils
from paasng.infras.iam.base.backends import BaseManagementBackend
from paasng.infras.iam.base.dto import UserGroup
from paasng.infras.iam.exceptions import (
    BKIAMApiError,
    BKIAMApiHTTPError,
    BKIAMCapabilityNotSupportedError,
)
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.infras.iam.shim import get_paas_system_id
from paasng.infras.iam.v4.http import BKIAMV4BaseClient
from paasng.infras.iam.v4.spaces import (
    build_log_permission_scope,
    build_monitor_permission_scope,
    build_paas_permission_scope,
    build_subject_scope,
)

logger = logging.getLogger(__name__)


class BKIAMV4ManagementBackend(BaseManagementBackend, BKIAMV4BaseClient):
    """权限中心 V4 的权限管理实现

    管理空间相关实现见 `#5 管理空间 V4 适配`，用户组与成员相关实现见
    `#6 用户组与成员管理 V4 适配`。
    """

    # ---------------- 管理空间 ----------------

    def create_management_space(
        self,
        app_code: str,
        app_name: str,
        init_member: str | None = None,
        bk_space_id: str | None = None,
    ) -> int:
        """创建应用管理空间，写入 paas/监控/日志 权限范围"""
        system_id = get_paas_system_id()
        permission_scope = build_paas_permission_scope(app_code, system_id)
        if bk_space_id:
            permission_scope.extend(self._build_observability_permission_scope(bk_space_id))

        return self._create_space(
            system_id=system_id,
            name=utils.gen_grade_manager_name(app_code),
            description=utils.gen_grade_manager_desc(app_code),
            init_member=init_member,
            permission_scope=permission_scope,
            reuse_on_conflict=lambda: self.fetch_management_space(app_code),
        )

    def fetch_management_space(self, app_code: str) -> int:
        """按名称查询应用管理空间 ID"""
        return self._fetch_space_id(get_paas_system_id(), utils.gen_grade_manager_name(app_code), app_code)

    def delete_management_space(self, space_id: int):
        """删除管理空间

        TODO: 待 IAM 补齐删除管理空间接口后在此接入（V3 对应 `v2_management_delete_grade_manager`）。
            受影响：应用删除、强制删除、平台管理下架时 IAM 侧空间不回收，会累积脏数据。
        """
        raise BKIAMCapabilityNotSupportedError("删除管理空间")

    def fetch_management_space_members(self, space_id: int) -> List[str]:
        """查询管理空间管理员，对应 V3 的分级管理员成员列表"""
        return self._retrieve_space_managers(get_paas_system_id(), space_id)

    def add_management_space_members(self, space_id: int, usernames: List[str], operator: str | None = None):
        """向管理空间添加管理员

        TODO: 待 IAM 补齐空间成员增删接口后在此接入。当前 `managers` 仅能在创建空间时指定。
            受影响：后续把用户提升为应用管理员时，无法同步为空间管理员。
        """
        raise BKIAMCapabilityNotSupportedError("添加管理空间成员")

    def delete_management_space_members(self, space_id: int, usernames: List[str], operator: str | None = None):
        """删除管理空间管理员

        TODO: 待 IAM 补齐空间成员增删接口后在此接入。
            受影响：移除应用管理员后对方仍保留空间管理员身份，可继续审批授权。
        """
        raise BKIAMCapabilityNotSupportedError("删除管理空间成员")

    def update_management_space_scopes(
        self, space_id: int, app_code: str, app_name: str, bk_space_id: str, operator: str | None = None
    ):
        """为管理空间追加监控、日志空间的授权范围

        V4 不需要该能力：管理空间均为新建，创建时已一次性写齐 bk_paas3、
        bk_monitorv3、bk_log_search 三个系统的权限范围（见 `create_management_space`），
        不存在 V3 那种「事后给存量分级管理员补授权范围」的场景。
        V3 对应接口为 `management_grade_managers_update`。
        仅当出现空间创建后才需要变更授权范围的新场景时才会走到这里；
        待权限中心补齐更新接口后再评估是否接入。不实现绕行方案。
        """
        raise BKIAMCapabilityNotSupportedError("更新管理空间的授权范围")

    # ---------------- 用户组与成员 ----------------

    def create_builtin_user_groups(self, space_id: int, app_code: str) -> List[UserGroup]:
        raise NotImplementedError("V4 内建用户组创建由子需求 #6 实现")

    def delete_user_groups(self, user_group_ids: List[int]):
        raise NotImplementedError("V4 用户组删除由子需求 #6 实现")

    def fetch_user_group_members(self, user_group_id: int) -> List[str]:
        # 实现时需经 BKIAMV4BaseClient.paginate 翻页，V4 列表接口单页上限为 100 条
        raise NotImplementedError("V4 用户组成员查询由子需求 #6 实现")

    def add_user_group_members(
        self, user_group_id: int, usernames: List[str], expired_after_days: int, operator: str | None = None
    ):
        raise NotImplementedError("V4 用户组成员添加由子需求 #6 实现")

    def delete_user_group_members(self, user_group_id: int, usernames: List[str], operator: str | None = None):
        raise NotImplementedError("V4 用户组成员删除由子需求 #6 实现")

    # ---------------- 授权 ----------------

    def grant_user_group_policies(self, app_code: str, app_name: str, groups: List[UserGroup]):
        raise NotImplementedError("V4 用户组授权由子需求 #6 实现")

    def revoke_user_group_policies(self, user_group_id: int, actions: List[AppAction]):
        raise NotImplementedError("V4 用户组权限回收由子需求 #6 实现")

    def grant_user_group_policies_in_bk_monitor(self, bk_space_id: str, app_name: str, groups: List[UserGroup]):
        raise NotImplementedError("V4 监控平台空间授权由子需求 #6 实现")

    def grant_user_group_policies_in_bk_log(self, bk_space_id: str, app_name: str, groups: List[UserGroup]):
        raise NotImplementedError("V4 日志平台空间授权由子需求 #6 实现")

    # ---------------- 内部方法 ----------------

    def _create_space(
        self,
        system_id: str,
        name: str,
        description: str,
        init_member: str | None,
        permission_scope: Sequence[Dict],
        reuse_on_conflict,
    ) -> int:
        data = {
            "name": name,
            "description": description,
            "managers": self._resolve_managers(init_member),
            "permission_scope": list(permission_scope),
            "subject_scope": build_subject_scope(),
        }
        try:
            resp = self.call(
                self.client.create_space,
                path_params={"system_id": system_id},
                data=data,
                for_write=True,
            )
        except BKIAMApiHTTPError as exc:
            if exc.status_code == HTTPStatus.CONFLICT:
                return reuse_on_conflict()
            raise

        space_id = (resp.get("data") or {}).get("id")
        if space_id is None:
            raise BKIAMApiError(f"create management space got unexpected response: {resp!r}")
        return int(space_id)

    def _build_observability_permission_scope(self, bk_space_id: str) -> List[Dict]:
        """写入监控 / 日志空间的业务运维角色，不实时拉取远端角色列表"""
        return [
            *build_monitor_permission_scope(bk_space_id),
            *build_log_permission_scope(bk_space_id),
        ]

    def _iter_spaces(self, system_id: str) -> Iterable[Dict]:
        return self.paginate(self.client.list_space, path_params={"system_id": system_id})

    def _fetch_space_id(self, system_id: str, space_name: str, resource_id: str) -> int:
        """按名称查询管理空间 ID

        TODO: 目前 IAM V4 不支持按名称查询，所以是遍历后匹配。 待权限中心支持后修改这里的实现。
        """

        for space in self._iter_spaces(system_id):
            if space.get("name") == space_name:
                return int(space["id"])
        raise BKIAMApiError(f"failed to find management space [{resource_id}]")

    def _retrieve_space_managers(self, system_id: str, space_id: int) -> List[str]:
        resp = self.call(
            self.client.retrieve_space,
            path_params={"system_id": system_id, "space_id": space_id},
        )
        return list((resp.get("data") or {}).get("managers") or [])

    def _resolve_managers(self, init_member: str | None) -> List[str]:
        """V4 要求 managers 不能为空；无初始管理员时回退到本次写操作的操作人"""
        if init_member:
            return [init_member]
        return [self.operator]
