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
import time
from http import HTTPStatus
from typing import Dict, Iterable, List, Sequence

from django.conf import settings

from paasng.infras.iam import utils
from paasng.infras.iam.base.backends import BaseManagementBackend
from paasng.infras.iam.base.constants import V4_MAX_PERMISSION_DAYS
from paasng.infras.iam.base.dto import UserGroup
from paasng.infras.iam.constants import APP_DEFAULT_ROLES, ONE_DAY_SECONDS, ResourceType
from paasng.infras.iam.exceptions import (
    BKIAMApiError,
    BKIAMApiHTTPError,
    BKIAMCapabilityNotSupportedError,
)
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.infras.iam.shim import get_paas_system_id
from paasng.infras.iam.v4.http import BKIAMV4BaseClient
from paasng.infras.iam.v4.spaces import (
    build_paas_permission_scope,
    build_subject_scope,
)
from paasng.platform.applications.constants import ApplicationRole

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
        init_members: List[str] | None = None,
        bk_space_id: str | None = None,
    ) -> int:
        """创建应用管理空间，写入本系统权限范围
        TODO 目前 iamV4 不支持跨系统授予角色（如监控/日志系统下的运营角色），待监控修复
        """
        system_id = get_paas_system_id()
        permission_scope = build_paas_permission_scope(app_code, system_id)
        if bk_space_id:
            logger.warning(
                "iam v4 create_space only accepts roles of the current system, "
                "skip monitor/log permission scope. bk_space_id=%s",
                bk_space_id,
            )

        return self._create_space(
            system_id=system_id,
            name=utils.gen_grade_manager_name(app_code),
            description=utils.gen_grade_manager_desc(app_code),
            managers=self._resolve_managers(init_members),
            permission_scope=permission_scope,
            reuse_on_conflict=lambda: self.fetch_management_space(app_code),
        )

    def fetch_management_space(self, app_code: str) -> int:
        """按名称查询应用管理空间 ID"""
        return self._fetch_space_id(get_paas_system_id(), utils.gen_grade_manager_name(app_code), app_code)

    def delete_management_space(self, space_id: int):
        """删除管理空间

        TODO: 待 IAM 补齐删除管理空间接口后在此接入（V3 对应 `v2_management_delete_grade_manager`）。
            当前只记录错误后返回，避免阻断应用删除；受影响：应用删除、强制删除、平台管理下架时
            IAM 侧空间不回收，会累积脏数据。
        """
        logger.error("iam v4 does not support deleting management space, skip. space_id=%s", space_id)

    def fetch_management_space_members(self, space_id: int) -> List[str]:
        """查询管理空间管理员，对应 V3 的分级管理员成员列表"""
        return self._retrieve_space_managers(get_paas_system_id(), space_id)

    def add_management_space_members(self, space_id: int, usernames: List[str], operator: str | None = None):
        """向管理空间添加管理员

        TODO: 待 IAM 补齐空间成员增删接口后在此接入。当前 `managers` 仅能在创建空间时指定，
            这里只记录错误后返回，避免阻断用户组成员变更；受影响：后续把用户提升为应用管理员时，
            无法同步为空间管理员。
        """
        logger.error("iam v4 does not support adding management space members, skip. space_id=%s", space_id)

    def delete_management_space_members(self, space_id: int, usernames: List[str], operator: str | None = None):
        """删除管理空间管理员

        TODO: 待 IAM 补齐空间成员增删接口后在此接入。当前只记录错误后返回，避免阻断用户组成员变更；
            受影响：移除应用管理员后对方仍保留空间管理员身份，可继续审批授权。
        """
        logger.error("iam v4 does not support deleting management space members, skip. space_id=%s", space_id)

    def update_management_space_scopes(
        self, space_id: int, app_code: str, app_name: str, bk_space_id: str, operator: str | None = None
    ):
        """为管理空间追加监控、日志空间的授权范围

        V4 不需要该能力：管理空间均为新建，创建时已一次性写齐 bk_paas3、
        bk_monitorv3、bk_log_search 三个系统的权限范围（见 `create_management_space`），
        不存在 V3 那种「事后给存量分级管理员补授权范围」的场景。
        V3 对应接口为 `management_grade_managers_update`。
        仅当出现空间创建后才需要变更授权范围的新场景时才会走到这里，只记录错误后返回，
        不实现绕行方案。
        """
        logger.error("iam v4 does not support updating management space scopes, skip. space_id=%s", space_id)

    # ---------------- 用户组与成员 ----------------

    def create_builtin_user_groups(
        self,
        space_id: int,
        app_code: str,
        app_name: str = "",
        init_members: List[str] | None = None,
    ) -> List[UserGroup]:
        """创建内建用户组。V4 创建时一次性写入成员与权限范围，减少中间失败态。

        TODO: 权限有效期按 V4 上限 365 天设置。该值受 V4 侧上限约束，
        平台侧暂不实现续期、到期巡检与到期提醒；到期处置方案待 IAM 提供官方路径
        """
        created: List[UserGroup] = []
        admin_members = _to_user_members(init_members or [])
        for role in APP_DEFAULT_ROLES:
            members = admin_members if role == ApplicationRole.ADMINISTRATOR else []
            group_id = self._create_or_reuse_group(
                space_id,
                name=utils.gen_user_group_name(app_code, role),
                description=utils.gen_user_group_desc(app_code, role),
                members=members,
                permissions=_build_group_permissions(app_code, role),
            )
            created.append(
                UserGroup(
                    id=group_id,
                    name=utils.gen_user_group_name(app_code, role),
                    role=int(role),
                    description=utils.gen_user_group_desc(app_code, role),
                )
            )
        return created

    def delete_user_groups(self, user_group_ids: List[int]):
        """删除指定的用户组

        V4 尚未提供删除用户组接口（V3 对应 `v2_management_grade_manager_delete_group`）。
        应用删除会调用本方法，缺接口时只记日志，避免阻断本地清理。
        待权限中心补齐删除接口后，在此处接入即可。
        """
        logger.error("iam v4 does not support deleting user groups, skip. group_ids=%s", user_group_ids)

    def fetch_user_group_members(self, user_group_id: int) -> List[str]:
        """查询用户组成员，经 paginate 自动翻页（单页上限 100），不静默截断。

        仅返回 type=user 的成员。平台成员体系按用户名处理，部门成员不纳入。
        """
        members = self.paginate(
            self.client.list_group_member,
            path_params={"system_id": get_paas_system_id(), "group_id": user_group_id},
        )
        return [item["id"] for item in members if item.get("type") == "user"]

    def add_user_group_members(
        self, user_group_id: int, usernames: List[str], expired_after_days: int, operator: str | None = None
    ):
        """向用户组添加成员。V4 加成员接口没有过期字段，有效期由创建用户组时的 permission_expired_at 统一约束。

        :param expired_after_days: 兼容 V3 签名，V4 不向 IAM 传递该字段。
        """
        self._mutate_group_members(self.client.add_group_member, user_group_id, usernames, operator=operator)

    def delete_user_group_members(self, user_group_id: int, usernames: List[str], operator: str | None = None):
        self._mutate_group_members(self.client.delete_group_member, user_group_id, usernames, operator=operator)

    # ---------------- 授权 ----------------

    def grant_user_group_policies(self, app_code: str, app_name: str, groups: List[UserGroup]):
        """为内建用户组授予开发者中心的权限

        V4 仅允许在 `system_mgmt_create_group` 时一次性指定权限范围，没有给已有用户组补授权的接口
        （V3 对应 `v2_management_groups_policies_grant`）。
        受影响的业务场景：角色权限调整后无法对存量用户组补授；`regrant_user_group_policies` 命令在 V4 下不可用。
        正常创建链路已在 `create_builtin_user_groups` 中写入权限，不应再调用本方法。
        待权限中心补齐更新用户组权限接口后，在此处接入即可。
        """
        raise BKIAMCapabilityNotSupportedError("grant policies to existing user groups")

    def revoke_user_group_policies(self, user_group_id: int, actions: List[AppAction]):
        """回收用户组的指定应用操作权限

        V4 尚未提供按操作回收用户组权限的接口（V3 对应 `v2_management_groups_policies_revoke_by_action`）。
        受影响的业务场景：角色权限收缩后无法对存量用户组回收多余操作。
        待权限中心补齐后，在此处接入即可。
        """
        raise BKIAMCapabilityNotSupportedError("revoke user group policies")

    def grant_user_group_policies_in_bk_monitor(self, bk_space_id: str, app_name: str, groups: List[UserGroup]):
        """为内建用户组授予监控平台的空间权限

        V4 没有给已有用户组补授权的接口，跨系统授权也无法在本系统 `create_group` 时写入。
        受影响的业务场景：应用接入监控后，管理员/开发者/运营者用户组无法获得监控空间权限。
        待权限中心补齐补授权接口且监控系统接入 V4 后，在此处接入即可。
        """
        raise BKIAMCapabilityNotSupportedError("grant policies to existing user groups (bk_monitor)")

    def grant_user_group_policies_in_bk_log(self, bk_space_id: str, app_name: str, groups: List[UserGroup]):
        """为内建用户组授予日志平台的空间权限

        V4 没有给已有用户组补授权的接口，跨系统授权也无法在本系统 `create_group` 时写入。
        受影响的业务场景：应用接入日志后，内建用户组无法获得日志空间权限。
        待权限中心补齐补授权接口且日志系统接入 V4 后，在此处接入即可。
        """
        raise BKIAMCapabilityNotSupportedError("grant policies to existing user groups (bk_log)")

    # ---------------- 内部方法 ----------------

    def _create_space(
        self,
        system_id: str,
        name: str,
        description: str,
        managers: List[str],
        permission_scope: Sequence[Dict],
        reuse_on_conflict,
    ) -> int:
        data = {
            "name": name,
            "description": description,
            "managers": managers,
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

    def _resolve_managers(self, init_members: List[str] | None = None) -> List[str]:
        """V4 要求 managers 不能为空；无初始管理员时回退到本次写操作的操作人"""
        if init_members:
            return list(init_members)
        return [self.operator]

    def _create_or_reuse_group(
        self,
        space_id: int,
        name: str,
        description: str,
        members: List[Dict],
        permissions: List[Dict],
    ) -> int:
        data = {
            "name": name,
            "description": description,
            "members": members,
            "permissions": permissions,
            # 按 V4 允许的最大有效期设置。该值受 V4 侧上限约束，平台侧暂不实现续期
            "permission_expired_at": int(time.time()) + V4_MAX_PERMISSION_DAYS * ONE_DAY_SECONDS,
        }
        path_params = {"system_id": get_paas_system_id(), "space_id": space_id}
        try:
            resp = self.call(self.client.create_group, path_params=path_params, data=data, for_write=True)
        except BKIAMApiHTTPError as exc:
            if exc.status_code != HTTPStatus.CONFLICT:
                raise
            return self._fetch_group_id_by_name(space_id, name)

        group_id = (resp.get("data") or {}).get("id")
        if group_id is None:
            raise BKIAMApiError(
                "create user group succeeded but response has no id", request_id=resp.get("request_id")
            )
        return group_id

    def _fetch_group_id_by_name(self, space_id: int, name: str) -> int:
        """同名用户组已存在时回查并复用其 ID，不产生重复用户组"""
        for group in self.paginate(
            self.client.list_group,
            path_params={"system_id": get_paas_system_id(), "space_id": space_id},
        ):
            if group.get("name") == name:
                return group["id"]
        raise BKIAMApiError(f"failed to find existing user group [{name}]")

    def _mutate_group_members(self, operation, user_group_id: int, usernames: List[str], operator: str | None = None):
        """批量增删组成员"""
        usernames = [name for name in usernames if name != settings.ADMIN_USERNAME]
        if not usernames:
            return

        self.call_in_batches(
            operation,
            usernames,
            lambda batch: {"members": _to_user_members(batch)},
            path_params={"system_id": get_paas_system_id(), "group_id": user_group_id},
            operator=operator,
        )


def _to_user_members(usernames: List[str]) -> List[Dict]:
    # 参考 v3 逻辑，admin 用户拥有全量权限，不应占用配额也不需要授权
    return [{"id": name, "type": "user"} for name in usernames if name != settings.ADMIN_USERNAME]


def _build_group_permissions(app_code: str, role: ApplicationRole) -> List[Dict]:
    """组装 V4 用户组权限范围：角色 ID + 应用资源实例，不再自行展开 action 列表。"""
    app_role = utils.APPLICATION_ROLE_TO_APP_ROLE[role]
    resource_type = str(ResourceType.Application)
    return [
        {
            "id": str(app_role),
            "resources": [
                {
                    "related_resource_type_id": resource_type,
                    "is_any": False,
                    "instances": [{"id": app_code, "type": resource_type}],
                }
            ],
        }
    ]
