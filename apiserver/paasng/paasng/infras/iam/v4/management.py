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

from typing import List, Optional

from paasng.infras.iam.base.backends import BaseManagementBackend
from paasng.infras.iam.base.dto import UserGroup
from paasng.infras.iam.exceptions import BKIAMCapabilityNotSupportedError
from paasng.infras.iam.v4.http import BKIAMV4BaseClient


class BKIAMV4ManagementBackend(BaseManagementBackend, BKIAMV4BaseClient):
    """权限中心 V4 的权限管理实现

    管理空间相关实现见 `#5 管理空间 V4 适配`，用户组与成员相关实现见
    `#6 用户组与成员管理 V4 适配`。
    """

    # ---------------- 管理空间 ----------------

    def create_management_space(self, app_code: str, app_name: str, init_member: Optional[str] = None) -> int:
        raise NotImplementedError("V4 管理空间创建由子需求 #5 实现")

    def fetch_management_space(self, app_code: str) -> int:
        raise NotImplementedError("V4 管理空间查询由子需求 #5 实现")

    def delete_management_space(self, space_id: int):
        raise NotImplementedError("V4 管理空间删除由子需求 #5 实现")

    def fetch_management_space_members(self, space_id: int) -> List[str]:
        raise NotImplementedError("V4 管理空间成员查询由子需求 #5 实现")

    def add_management_space_members(self, space_id: int, usernames: List[str], operator: Optional[str] = None):
        raise NotImplementedError("V4 管理空间成员添加由子需求 #5 实现")

    def delete_management_space_members(self, space_id: int, usernames: List[str], operator: Optional[str] = None):
        raise NotImplementedError("V4 管理空间成员删除由子需求 #5 实现")

    def update_management_space_scopes(
        self, space_id: int, app_code: str, app_name: str, bk_space_id: str, operator: Optional[str] = None
    ):
        """为管理空间追加监控、日志空间的授权范围

        V4 尚未提供管理空间的更新接口（V3 对应 `management_grade_managers_update`）。
        受影响的业务场景：V3 下应用创建后再申请监控/日志空间时，需要回头给分级管理员补授权范围。
        V4 的做法是在创建管理空间时一次性写齐监控与日志的授权范围（见 `#5`），
        因此正常链路不会走到这里；仅当出现空间创建后才需要变更授权范围的场景时才会触发。
        待权限中心补齐更新接口后，在此处接入即可。
        """
        raise BKIAMCapabilityNotSupportedError(
            "更新管理空间的授权范围",
            "V4 应在创建管理空间时一次性写齐监控、日志的授权范围",
        )

    # ---------------- 用户组与成员 ----------------

    def create_builtin_user_groups(self, space_id: int, app_code: str) -> List[UserGroup]:
        raise NotImplementedError("V4 内建用户组创建由子需求 #6 实现")

    def delete_user_groups(self, user_group_ids: List[int]):
        raise NotImplementedError("V4 用户组删除由子需求 #6 实现")

    def fetch_user_group_members(self, user_group_id: int) -> List[str]:
        # 实现时需经 BKIAMV4BaseClient.paginate 翻页，V4 列表接口单页上限为 100 条
        raise NotImplementedError("V4 用户组成员查询由子需求 #6 实现")

    def add_user_group_members(
        self, user_group_id: int, usernames: List[str], expired_after_days: int, operator: Optional[str] = None
    ):
        raise NotImplementedError("V4 用户组成员添加由子需求 #6 实现")

    def delete_user_group_members(self, user_group_id: int, usernames: List[str], operator: Optional[str] = None):
        raise NotImplementedError("V4 用户组成员删除由子需求 #6 实现")

    # ---------------- 授权 ----------------

    def grant_user_group_policies(self, app_code: str, app_name: str, groups: List[UserGroup]):
        raise NotImplementedError("V4 用户组授权由子需求 #6 实现")

    def revoke_user_group_policies(self, user_group_id: int, actions: List[str]):
        raise NotImplementedError("V4 用户组权限回收由子需求 #6 实现")

    def grant_user_group_policies_in_bk_monitor(self, bk_space_id: str, app_name: str, groups: List[UserGroup]):
        raise NotImplementedError("V4 监控平台空间授权由子需求 #6 实现")

    def grant_user_group_policies_in_bk_log(self, bk_space_id: str, app_name: str, groups: List[UserGroup]):
        raise NotImplementedError("V4 日志平台空间授权由子需求 #6 实现")
