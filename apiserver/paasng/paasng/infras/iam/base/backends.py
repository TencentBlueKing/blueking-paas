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

"""V3 / V4 两套实现共同遵循的抽象接口

约定：
- 租户标识逐请求传入，实现不得使用进程级缓存的租户上下文
- 鉴权失败一律返回 False 或抛异常，不因 IAM 不可达而默认放行
- 目标版本尚未提供的能力，实现须抛 `BKIAMCapabilityNotSupportedError`，不得静默返回成功
- 管理类调用失败时抛 `paasng.infras.iam.exceptions` 中的异常，并携带 IAM 侧 request_id

note: 鉴权类调用的异常已跨版本统一到 `BKIAMGatewayServiceError` 之下——V3 将 SDK 的
    `iam.exceptions.AuthAPIError` 包装为 `BKIAMAuthCheckError`，V4 抛出的 `BKIAMApiError`
    系列同属该基类。调用方捕获基类即可，不再 import SDK 的异常类型。
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, List

from django.db.models import Q

from paasng.infras.iam.base.dto import AuthResource, UserGroup

if TYPE_CHECKING:
    from paasng.infras.iam.permissions.resources.application import AppAction


class BaseAuthBackend(ABC):
    """鉴权判定接口

    对应 V3 的 `bk-iam` Python SDK 与 V4 的鉴权类 HTTP 接口。
    """

    @abstractmethod
    def resource_type_allowed(self, username: str, tenant_id: str, action_id: str, use_cache: bool = False) -> bool:
        """判断用户是否具备某个操作的权限（与资源实例无关，如创建某资源）

        :param use_cache: 是否使用本地缓存校验。仅用于 view 类非敏感操作
        """

    @abstractmethod
    def resource_inst_allowed(
        self,
        username: str,
        tenant_id: str,
        action_id: str,
        resource: AuthResource,
        use_cache: bool = False,
    ) -> bool:
        """判断用户对某个资源实例是否具有指定操作的权限"""

    @abstractmethod
    def resource_inst_multi_actions_allowed(
        self, username: str, tenant_id: str, action_ids: List[str], resource: AuthResource
    ) -> Dict[str, bool]:
        """判断用户对单个资源实例是否具有多个操作的权限

        操作数超过版本约定的批量上限时，由实现自动分批后合并结果。

        :returns: 形如 {'view_basic_info': True, 'edit_basic_info': False}
        """

    @abstractmethod
    def build_resource_filter(
        self, username: str, tenant_id: str, action_id: str, key_mapping: Dict[str, str] | None = None
    ) -> Q | None:
        """策略下推：将用户在某操作上的权限策略转换为 Django ORM 过滤条件

        :param key_mapping: IAM 侧资源字段到 ORM 字段的映射，如 {"application.id": "code"}
        :returns: 过滤条件；None 表示未能取得策略，调用方需按无权限处理

        note: PaaS 2.0 遗留系统（`bk_paas`）的 SQL 过滤场景不在本契约内，
            该系统未在 V4 侧注册模型，仍走 V3 专有实现。
        """


class BaseManagementBackend(ABC):
    """权限管理接口

    对应 V3 的分级管理员/用户组管理接口与 V4 的管理空间/用户组管理接口。
    实现由 `tenant_id` 构造，每次调用均携带该租户标识。
    """

    tenant_id: str

    # ---------------- 管理空间（V3 语义为分级管理员） ----------------

    @abstractmethod
    def create_management_space(
        self,
        app_code: str,
        app_name: str,
        init_members: List[str] | None = None,
        bk_space_id: str | None = None,
    ) -> int:
        """创建管理空间，若已存在则返回已有空间的 ID

        监控/日志权限的写入时机两个版本不同：V3 由后续的更新操作事后补齐（该权限是后来新增的
        逻辑，为让存量分级管理员平滑迁移，只能通过更新补充）。V4 `create_space` 只接受本系统
        角色，跨系统范围写入会被拒绝，因此 V4 创建时只写 bk_paas3 权限范围。

        :param init_members: 初始管理员用户名列表。V3、V4 创建时都会写入；为空则该空间没有管理员。
            V4 暂无空间成员增删接口，存量迁移必须一次把全部管理员带上
        :param bk_space_id: 蓝鲸监控空间在权限中心的资源 ID。V3 忽略该参数，仍通过更新分级
            管理员事后补齐；V4 当前忽略，不能把监控/日志角色写入本系统管理空间
        :returns: 管理空间 ID
        """

    @abstractmethod
    def fetch_management_space(self, app_code: str) -> int:
        """按名称查询管理空间 ID"""

    @abstractmethod
    def delete_management_space(self, space_id: int):
        """删除管理空间"""

    @abstractmethod
    def fetch_management_space_members(self, space_id: int) -> List[str]:
        """查询管理空间的成员列表"""

    @abstractmethod
    def add_management_space_members(self, space_id: int, usernames: List[str], operator: str | None = None):
        """向管理空间添加成员"""

    @abstractmethod
    def delete_management_space_members(self, space_id: int, usernames: List[str], operator: str | None = None):
        """删除管理空间的成员"""

    @abstractmethod
    def update_management_space_scopes(
        self, space_id: int, app_code: str, app_name: str, bk_space_id: str, operator: str | None = None
    ):
        """为管理空间追加监控、日志空间的授权范围

        note: V4 暂未提供管理空间的更新接口。V4 下应在创建空间时一次性写齐授权范围，
            该方法在 V4 实现中记录错误后返回，避免阻断监控/日志接入。
        """

    # ---------------- 用户组与成员 ----------------

    @abstractmethod
    def create_builtin_user_groups(
        self,
        space_id: int,
        app_code: str,
        app_name: str = "",
        init_members: List[str] | None = None,
    ) -> List[UserGroup]:
        """创建内建用户组（管理员、开发者、运营者），若已存在则返回已有用户组

        :param app_name: 应用名称。V4 创建时用于组装权限范围
        :param init_members: 初始成员。V4 在创建管理员组时一次性写入；V3 忽略该参数
        """

    @abstractmethod
    def delete_user_groups(self, user_group_ids: List[int]):
        """删除指定的用户组"""

    @abstractmethod
    def fetch_user_group_members(self, user_group_id: int) -> List[str]:
        """查询用户组的成员名称列表，条目数超过单页上限时由实现自动翻页"""

    @abstractmethod
    def add_user_group_members(
        self, user_group_id: int, usernames: List[str], expired_after_days: int, operator: str | None = None
    ):
        """向用户组添加成员

        :param expired_after_days: X 天后权限过期，-1 表示永不过期。
            note: V4 在用户组层面限制有效期上限为一年，传入 -1 时实际按一年生效，
                续期方案待权限中心确认，详见 `#6` 子需求说明
        """

    @abstractmethod
    def delete_user_group_members(self, user_group_id: int, usernames: List[str], operator: str | None = None):
        """删除用户组的成员"""

    # ---------------- 授权 ----------------

    @abstractmethod
    def grant_user_group_policies(self, app_code: str, app_name: str, groups: List[UserGroup]):
        """为内建用户组授予开发者中心的权限"""

    @abstractmethod
    def revoke_user_group_policies(self, user_group_id: int, actions: List["AppAction"]):
        """回收用户组的指定应用操作权限"""

    @abstractmethod
    def grant_user_group_policies_in_bk_monitor(self, bk_space_id: str, app_name: str, groups: List[UserGroup]):
        """为内建用户组授予监控平台的空间权限

        :param bk_space_id: 蓝鲸监控的空间 ID，注意该值是负数
        """

    @abstractmethod
    def grant_user_group_policies_in_bk_log(self, bk_space_id: str, app_name: str, groups: List[UserGroup]):
        """为内建用户组授予日志平台的空间权限"""


class BaseModelRegistryBackend(ABC):
    """权限模型注册接口

    V3 通过 SDK 的 migration JSON 模板以 upsert 语义注册模型；
    V4 改为标准 REST 接口，需由实现自行保证幂等，详见 `#2` 子需求。
    """

    @abstractmethod
    def sync_system(self):
        """同步系统定义"""

    @abstractmethod
    def sync_resource_types(self):
        """同步资源类型定义"""

    @abstractmethod
    def sync_actions(self):
        """同步操作定义

        note: V4 的操作模型不再提供 `related_actions`，V3 声明的操作依赖关系在 V4 侧丢失
        """

    @abstractmethod
    def sync_roles(self):
        """同步角色定义（V4 新增概念，V3 侧为权限模板/自定义权限）"""
