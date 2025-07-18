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

import typing
from typing import List, Optional

from django.conf import settings

from paasng.bk_plugins.pluginscenter.bk_user.client import BkUserManageClient
from paasng.bk_plugins.pluginscenter.constants import (
    GrayReleaseStatus,
    PluginReleaseStatus,
    PluginRole,
    ReleaseStageInvokeMethod,
    ReleaseStrategy,
)
from paasng.bk_plugins.pluginscenter.exceptions import error_codes
from paasng.bk_plugins.pluginscenter.iam_adaptor.management import shim as members_api
from paasng.bk_plugins.pluginscenter.itsm_adaptor.client import ItsmClient
from paasng.bk_plugins.pluginscenter.itsm_adaptor.constants import ApprovalServiceName, ItsmTicketStatus
from paasng.bk_plugins.pluginscenter.models import (
    ApprovalService,
    PluginDefinition,
    PluginInstance,
    PluginRelease,
    PluginVisibleRange,
)
from paasng.bk_plugins.pluginscenter.models.instances import is_release_strategy_organization_changed
from paasng.bk_plugins.pluginscenter.thirdparty.members import sync_members
from paasng.infras.iam.exceptions import BKIAMGatewayServiceError

if typing.TYPE_CHECKING:
    from paasng.bk_plugins.pluginscenter.models.instances import ItsmDetail


# ITSM 提单字段中必填字段的占位符
ITSM_FIELD_PLACEHOLDER = "--"


def submit_create_approval_ticket(pd: PluginDefinition, plugin: PluginInstance, operator: str):
    """提交创建申请单据"""
    basic_fields = _get_basic_fields(pd, plugin)
    # 查询上线审批服务ID
    service_id = ApprovalService.objects.get(service_name=ApprovalServiceName.CREATE_APPROVAL.value).service_id

    # 单据结束的时候，itsm 会调用 callback_url 告知审批结果，回调地址为开发者中心后台 API 的地址
    paas_url = f"{settings.BK_IAM_RESOURCE_API_HOST}/backend"
    callback_url = f"{paas_url}/open/api/itsm/bkplugins/" + f"{pd.identifier}/plugins/{plugin.id}/"

    # 组装提单数据,包含插件的基本信息
    basic_fields = _get_basic_fields(pd, plugin)
    title_fields = [{"key": "title", "value": f"插件[{plugin.name}]创建审批"}]
    fields = basic_fields + title_fields

    # 提交 itsm 申请单据
    client = ItsmClient()
    itsm_detail = client.create_ticket(service_id, operator, callback_url, fields)

    plugin.itsm_detail = itsm_detail
    plugin.save(update_fields=["itsm_detail"])


def submit_online_approval_ticket(pd: PluginDefinition, plugin: PluginInstance, version: PluginRelease, operator: str):
    """提交上线申请申请单据"""
    current_stage = version.current_stage
    if not current_stage or current_stage.invoke_method != ReleaseStageInvokeMethod.ITSM.value:
        raise ValueError("this stage is not invoked by itsm")
    if current_stage.status != PluginReleaseStatus.INITIAL:
        raise ValueError("itsm stage is not an initialization state and cannot be triggered")

    # 组装提单数据,包含插件的基本信息和版本信息
    basic_fields = _get_basic_fields(pd, plugin)
    advanced_fields = _get_advanced_fields(pd, plugin, version)
    title_fields = [{"key": "title", "value": f"插件[{plugin.name}]上线审批"}]
    fields = basic_fields + advanced_fields + title_fields

    # 查询上线审批服务ID
    service_id = ApprovalService.objects.get(service_name=ApprovalServiceName.ONLINE_APPROVAL.value).service_id

    # 单据结束的时候，itsm 会调用 callback_url 告知审批结果，回调地址为开发者中心后台 API 的地址
    paas_url = f"{settings.BK_IAM_RESOURCE_API_HOST}/backend"
    callback_url = (
        f"{paas_url}/open/api/itsm/bkplugins/"
        + f"{pd.identifier}/plugins/{plugin.id}/releases/{version.id}/stages/{current_stage.id}/"
    )

    # 提交 itsm 申请单据
    client = ItsmClient()
    itsm_detail = client.create_ticket(service_id, operator, callback_url, fields)

    current_stage.status = PluginReleaseStatus.PENDING
    current_stage.itsm_detail = itsm_detail
    current_stage.save(update_fields=["status", "itsm_detail"])


def submit_canary_release_ticket(
    pd: PluginDefinition, plugin: PluginInstance, version: PluginRelease, operator: str
) -> "ItsmDetail":
    """提交灰度发布申请单据"""
    # 发布策略
    release_strategy = version.latest_release_strategy
    if not release_strategy:
        raise ValueError(
            "The current version does not have a release strategy set, so the gray approval process cannot be initiated."
        )

    # 可见范围
    visible_range_obj = PluginVisibleRange.get_or_initialize_with_default(plugin=plugin)
    # 插件概览页面的地址
    plugin_url = f"{settings.BK_IAM_RESOURCE_API_HOST}/plugin-center/plugin/{pd.identifier}/{plugin.id}/summary"
    # 灰度发布在 ITSM 中展示的字段
    canary_fields = [
        # 提单人，ITSM 回调的信息不准确，需要自己存储获取
        {"key": "submitter", "value": operator},
        # 插件概览页面地址
        {"key": "plugin_url", "value": plugin_url},
        # 发布策略的字段
        {"key": "strategy_id", "value": release_strategy.id},
        {"key": "strategy", "value": release_strategy.get_strategy_display()},
        {"key": "strategy_bkci_project", "value": _get_bkci_project_display_name(release_strategy.bkci_project)},
        {"key": "strategy_organization", "value": _get_organization_display_name(release_strategy.organization)},
        # 可见范围的字段
        {"key": "range_bkci_project", "value": _get_bkci_project_display_name(visible_range_obj.bkci_project)},
        {"key": "range_organization", "value": _get_organization_display_name(visible_range_obj.organization)},
    ]

    # 组装提单数据,包含插件的基本信息和灰度发布信息
    basic_fields = _get_basic_fields(pd, plugin)
    title_fields = [{"key": "title", "value": f"插件[{plugin.name}]灰度发布审批"}]
    itsm_fields = basic_fields + title_fields + canary_fields

    service_name = release_strategy.get_itsm_service_name(is_release_strategy_organization_changed(version))
    service_id = ApprovalService.objects.get(service_name=service_name).service_id

    # 灰度审批是由插件的管理员审批，需要单独添加审批字段
    if release_strategy.strategy == ReleaseStrategy.GRAY:
        plugin_admins = members_api.fetch_role_members(plugin, PluginRole.ADMINISTRATOR)
        itsm_fields += [
            # 插件管理员
            {"key": "plugin_admins", "value": ",".join(plugin_admins)},
        ]

    # 单据结束的时候，itsm 会调用 callback_url 告知审批结果，回调地址为开发者中心后台 API 的地址
    paas_url = f"{settings.BK_IAM_RESOURCE_API_HOST}/backend"
    callback_url = (
        f"{paas_url}/open/api/itsm/bkplugins/"
        + f"{pd.identifier}/plugins/{plugin.id}/releases/{version.id}/strategy/{release_strategy.id}/"
    )

    # 提审批单据前，先将审批人（平台管理员）添加到插件的管理员中
    add_approver_to_plugin_admins(plugin, service_name, operator)
    # 提交 itsm 申请单据
    client = ItsmClient()
    itsm_detail = client.create_ticket(service_id, operator, callback_url, itsm_fields)
    release_strategy.itsm_detail = itsm_detail
    release_strategy.save()
    # 更新版本的灰度状态
    release_status = (
        GrayReleaseStatus.FULL_APPROVAL_IN_PROGRESS
        if release_strategy.strategy == ReleaseStrategy.FULL
        else GrayReleaseStatus.GRAY_APPROVAL_IN_PROGRESS
    )
    version.gray_status = release_status
    version.save()
    return itsm_detail


def submit_visible_range_ticket(
    pd: PluginDefinition,
    plugin: PluginInstance,
    operator: str,
    visible_range_obj: "PluginVisibleRange",
    bkci_project: Optional[list],
    organization: Optional[list],
) -> "ItsmDetail":
    # 查询上线审批服务ID
    service_name = ApprovalServiceName.VISIBLE_RANGE_APPROVAL
    service_id = ApprovalService.objects.get(service_name=service_name).service_id

    # 单据结束的时候，itsm 会调用 callback_url 告知审批结果，回调地址为开发者中心后台 API 的地址
    paas_url = f"{settings.BK_IAM_RESOURCE_API_HOST}/backend"
    callback_url = f"{paas_url}/open/api/itsm/bkplugins/" + f"{pd.identifier}/plugins/{plugin.id}/visible_range/"
    # 插件概览页面的地址
    plugin_url = f"{settings.BK_IAM_RESOURCE_API_HOST}/plugin-center/plugin/{pd.identifier}/{plugin.id}/summary"
    visible_range_fields = [
        # 提单人，ITSM 回调的信息不准确，需要自己存储获取
        {"key": "submitter", "value": operator},
        # 插件概览页面地址
        {"key": "plugin_url", "value": plugin_url},
        # 需要单独存储原始数据，用户审批成功后回调后用于更新 DB 的可见范围
        {"key": "origin_bkci_project", "value": bkci_project},
        {"key": "origin_organization", "value": organization},
        {"key": "bkci_project", "value": _get_bkci_project_display_name(bkci_project)},
        {"key": "organization", "value": _get_organization_display_name(organization)},
        {"key": "current_bkci_project", "value": _get_bkci_project_display_name(visible_range_obj.bkci_project)},
        {"key": "current_organization", "value": _get_organization_display_name(visible_range_obj.organization)},
    ]

    # 组装提单数据,包含插件的基本信息、可见范围修改前的值，修改后的值
    basic_fields = _get_basic_fields(pd, plugin)
    title_fields = [{"key": "title", "value": f"插件[{plugin.name}]可见范围修改审批"}]
    fields = basic_fields + title_fields + visible_range_fields

    # 提审批单据前，先将审批人（平台管理员）添加到插件的管理员中
    add_approver_to_plugin_admins(plugin, service_name, operator)
    # 提交 itsm 申请单据
    client = ItsmClient()
    itsm_detail = client.create_ticket(service_id, operator, callback_url, fields)
    return itsm_detail


def get_ticket_status(sn: str) -> dict:
    """查询 itsm 单据状态

    itsm 返回数据格式：{
        "ticket_url": "https://blueking.com/#/commonInfo?id=6&activeNname=all&router=request",
        "operations": [
                {
                    "can_operate": true,
                    "name": "撤单",
                    "key": "WITHDRAW"
                },
                {
                    "can_operate": true,
                    "name": "恢复",
                    "key": "UNSUSPEND"
                }
            ],
        "current_status": "SUSPENDED"
    }
    """
    client = ItsmClient()
    data = client.get_ticket_status(sn)

    operation_dict = {d["key"]: d["can_operate"] for d in data["operations"]}
    return {
        "ticket_url": data["ticket_url"],
        "current_status": data["current_status"],
        "current_status_display": ItsmTicketStatus.get_choice_label(data["current_status"]),
        "can_withdraw": operation_dict.get("WITHDRAW", False),
    }


def is_itsm_ticket_closed(sn: str) -> bool:
    """
    ITSM 审批单据流程是否已经结束

    :param sn: 审批单据 ID
    """
    client = ItsmClient()
    ticket_status = client.get_ticket_status(sn)["current_status"]
    return ticket_status in ItsmTicketStatus.completed_status()


def _get_basic_fields(pd: PluginDefinition, plugin: PluginInstance) -> List[dict]:
    """获取插件的基本字段信息，可用于创建申请提单 和 上线申请提单"""
    fields = [
        {
            "key": "plugin_type",
            "value": pd.name,
        },
        {
            "key": "plugin_id",
            "value": plugin.id,
        },
        {
            "key": "plugin_name",
            "value": plugin.name,
        },
        {
            "key": "repository",
            "value": plugin.repository,
        },
        {
            "key": "creator",
            "value": plugin.creator.username,
        },
        {
            "key": "approver",
            # 审批者为插件的平台管理员
            "value": ",".join(pd.administrator),
        },
    ]
    return fields


def _get_advanced_fields(
    pd: PluginDefinition,
    plugin: PluginInstance,
    version: PluginRelease,
) -> List[dict]:
    """获取插件的版本、市场相关字段信息，可用于上线申请提单"""
    fields = [
        {
            "key": "source_version_name",
            "value": version.source_version_name,
        },
        {
            "key": "version",
            "value": version.version,
        },
        {
            "key": "comment",
            "value": version.comment,
        },
        {
            "key": "version_url",
            "value": f"{settings.PLUGIN_CENTER_URL}/plugin/{pd.identifier}/{plugin.id}/version-release?release_id={version.id}",
        },
    ]
    return fields


def _get_organization_display_name(organization: Optional[List[dict]]) -> str:
    """
    Display only the organization names, separated by semicolons if there are multiple.
    Show a placeholder if empty (ITSM does not allow empty data).
    """
    if not organization:
        return ITSM_FIELD_PLACEHOLDER

    organization_names = [r["name"] for r in organization]
    return ";".join(organization_names)


def _get_bkci_project_display_name(bkci_project: Optional[List[str]]) -> str:
    """
    Multiple projects separated by semicolons.
    Show a placeholder if empty (ITSM does not allow passing empty data).
    """
    if not bkci_project:
        return ITSM_FIELD_PLACEHOLDER

    return ";".join(bkci_project)


def _get_leader_by_user(username: str) -> list:
    client = BkUserManageClient()
    user_detail = client.get_user_detail(username)
    return [u.username for u in user_detail.leader]


def _add_users_to_plugin_role(plugin: PluginInstance, usernames: list, role: PluginRole):
    """添加用户到插件角色

    :param plugin: 插件实例
    :param usernames: 需要添加的用户名列表
    :param role: 目标角色
    """
    members = members_api.fetch_plugin_members(plugin)

    if role == PluginRole.ADMINISTRATOR:
        # 要添加的角色是管理员：如果用户已经是管理员，无需操作；如果用户是开发者，需要先删除开发者角色，再添加为管理员
        existing_members = {m.username for m in members if m.role.id == role}
    else:
        # 要添加的角色是开发者：用户已经是插件成员，就不需要操作了
        existing_members = {m.username for m in members}

    users_to_add = set(usernames) - existing_members
    if not users_to_add:
        return

    try:
        # 管理员角色需要： 先删除用户在插件中的所有权限，再添加为管理员。避免用户已经是开发者角色，再添加为管理员会报错
        if role == PluginRole.ADMINISTRATOR:
            members_api.remove_user_all_roles(plugin, list(users_to_add))
        members_api.add_role_members(plugin, role=role, usernames=list(users_to_add))
    except BKIAMGatewayServiceError as e:
        raise error_codes.MEMBERSHIP_UPDATE_FAILED.f(
            f"Failed to add user({usernames}) as plugin({plugin.id}) {role}: {e.message}"
        )

    # 同步成员到第三方系统
    sync_members(pd=plugin.pd, instance=plugin)
    return


def add_approver_to_plugin_admins(plugin: PluginInstance, service_name: str, operator: str):
    """将审批者提前添加到插件管理员中，方便其跟进插件状态"""
    # 按组织灰度审批，审批者为提单者 leader
    if service_name == ApprovalServiceName.CODECC_ORG_GRAY_RELEASE_APPROVAL:
        operator_leaders = _get_leader_by_user(operator)
        _add_users_to_plugin_role(plugin, operator_leaders, PluginRole.DEVELOPER)
    # 全量发布、可见范围修改：平台管理员审批
    elif service_name in [
        ApprovalServiceName.CODECC_FULL_RELEASE_APPROVAL,
        ApprovalServiceName.VISIBLE_RANGE_APPROVAL,
    ]:
        _add_users_to_plugin_role(plugin, plugin.pd.administrator, PluginRole.ADMINISTRATOR)
