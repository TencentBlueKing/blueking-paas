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

import logging
import time
from typing import List

from bkapi_client_core.exceptions import APIGatewayResponseError
from django.conf import settings
from django.utils.functional import SimpleLazyObject

from paasng.bk_plugins.pluginscenter.constants import PluginRole
from paasng.bk_plugins.pluginscenter.iam_adaptor import definitions
from paasng.bk_plugins.pluginscenter.iam_adaptor.constants import (
    DEFAULT_PAGE,
    FETCH_USER_GROUP_MEMBERS_LIMIT,
    NEVER_EXPIRE_TIMESTAMP,
    ONE_DAY_SECONDS,
    PluginPermissionActions,
    ResourceType,
)
from paasng.bk_plugins.pluginscenter.thirdparty.utils import registry_i18n_hook
from paasng.infras.iam.apigw.client import Client
from paasng.infras.iam.apigw.client import Group as BKIAMGroup
from paasng.infras.iam.exceptions import BKIAMApiError, BKIAMGatewayServiceError

logger = logging.getLogger(__name__)


def calc_expired_at(expire_after_days: int) -> int:
    """计算过期的时间戳，若传入的过期天数为负数，则表示永不过期"""
    if expire_after_days < 0:
        return NEVER_EXPIRE_TIMESTAMP

    return int(time.time()) + expire_after_days * ONE_DAY_SECONDS


class BKIAMClient:
    """bk-iam 通过 APIGW 提供的管理端 API client"""

    def __init__(self):
        client = Client(endpoint=settings.BK_API_URL_TMPL, stage=settings.BK_IAM_APIGW_SERVICE_STAGE)
        client.update_bkapi_authorization(
            bk_app_code=settings.BK_APP_CODE,
            bk_app_secret=settings.BK_APP_SECRET,
        )
        registry_i18n_hook(client.session)
        self.client: BKIAMGroup = client.api

    def create_grade_manager(
        self, plugin_resource: definitions.PluginIAMResource, manager_definition: definitions.GradeManager
    ) -> int:
        """在权限中心上为插件注册分级管理员

        :param plugin: 蓝鲸插件
        :returns: 分级管理员 ID
        """
        data = {
            "system": settings.IAM_PLUGINS_CENTER_SYSTEM_ID,
            "name": manager_definition.name,
            "description": manager_definition.description,
            "members": [plugin_resource.admin],
            # 仅可对指定的单个插件授权
            "authorization_scopes": [
                {
                    "system": settings.IAM_PLUGINS_CENTER_SYSTEM_ID,
                    "actions": [
                        {"id": action}
                        for action in PluginPermissionActions.get_choices_by_role(PluginRole.ADMINISTRATOR)
                    ],
                    "resources": [
                        {
                            "system": settings.IAM_PLUGINS_CENTER_SYSTEM_ID,
                            "type": ResourceType.PLUGIN,
                            "paths": [
                                [
                                    {
                                        "system": settings.IAM_PLUGINS_CENTER_SYSTEM_ID,
                                        "type": ResourceType.PLUGIN,
                                        "id": plugin_resource.id,
                                        "name": plugin_resource.name,
                                    }
                                ]
                            ],
                        }
                    ],
                }
            ],
            # 可授权的人员范围为公司任意人
            "subject_scopes": [
                {
                    "type": "*",
                    "id": "*",
                }
            ],
        }

        try:
            resp = self.client.management_grade_managers(data=data)
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f"create grade managers error, detail: {e}")

        if resp.get("code") != 0:
            logger.exception(f"create iam grade managers error, message:{resp['message']} \n data: {data}")
            raise BKIAMApiError(resp["message"])

        return resp["data"]["id"]

    def fetch_grade_manager_members(self, grade_manager_id: int) -> List[str]:
        """
        获取某个分级管理员的成员列表

        :param grade_manager_id: 分级管理员 ID
        :returns: 分级管理员成员列表
        """
        try:
            resp = self.client.management_grade_manager_members(path_params={"id": grade_manager_id})
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f"get grade manager members error, detail: {e}")

        if resp.get("code") != 0:
            logger.exception(
                "get grade manager members error, grade_manager_id: {}, message:{}".format(
                    grade_manager_id, resp["message"]
                )
            )
            raise BKIAMApiError(resp["message"])

        return resp.get("data", [])

    def add_grade_manager_members(self, grade_manager_id: int, usernames: List[str]):
        """
        向某个分级管理员添加成员（分级管理员没有过期时间）

        :param grade_manager_id: 分级管理员 ID
        :param usernames: 待添加成员名称
        """
        path_params, data = {"id": grade_manager_id}, {"members": usernames}

        try:
            resp = self.client.management_add_grade_manager_members(path_params=path_params, data=data)
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f"add grade manager (id: {grade_manager_id}) members error, detail: {e}")

        if resp.get("code") != 0:
            logger.exception(
                "add grade manager (id: {}) members error, message:{} \n data: {}".format(
                    grade_manager_id, resp["message"], data
                )
            )
            raise BKIAMApiError(resp["message"])

    def delete_grade_manager_members(self, grade_manager_id: int, usernames: List[str]):
        """删除某个分级管理员的成员

        :param grade_manager_id: 分级管理员 ID
        :param usernames: 待删除的成员名称
        """
        path_params, params = {"id": grade_manager_id}, {"members": ",".join(usernames)}

        try:
            resp = self.client.management_delete_grade_manager_members(path_params=path_params, params=params)
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f"delete grade manager (id: {grade_manager_id}) members error, detail: {e}")

        if resp.get("code") != 0:
            logger.exception(
                "delete grade manager members error, message:{} \n id: {}, params: {}".format(
                    resp["message"], grade_manager_id, params
                )
            )
            raise BKIAMApiError(resp["message"])

    def create_user_groups(
        self, grade_manager_id: int, groups: List[definitions.PluginUserGroup]
    ) -> List[definitions.PluginUserGroup]:
        """为插件创建用户组（默认2个：管理员，开发者）

        :param grade_manager_id: 分级管理员 ID
        :param groups: 蓝鲸插件
        :returns: 用户组信息
        """
        path_params = {"system_id": settings.IAM_PLUGINS_CENTER_SYSTEM_ID, "id": grade_manager_id}
        data = {
            "groups": [
                {
                    "name": group.name,
                    "description": group.description,
                    # 只读用户组，设置为 True 后，分级管理员无法在权限中心产品上删除该用户组
                    "readonly": True,
                }
                for group in groups
            ]
        }

        try:
            resp = self.client.v2_management_grade_manager_create_groups(path_params=path_params, data=data)
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f"create user groups error, detail: {e}")

        if resp.get("code") != 0:
            logger.exception(
                "create user groups error, message:{} \n grade_manager_id: {}, data: {}".format(
                    resp["message"], grade_manager_id, data
                )
            )
            raise BKIAMApiError(resp["message"])

        # 按照顺序，填充申请创建得到的各个用户组的 ID
        user_group_ids = resp.get("data", [])
        for group, user_group_id in zip(groups, user_group_ids):
            group.id = int(user_group_id)
        return groups

    def delete_user_groups(self, user_group_ids: List[int]):
        """删除指定的用户组"""
        for group_id in user_group_ids:
            path_params = {"system_id": settings.IAM_PLUGINS_CENTER_SYSTEM_ID, "group_id": group_id}
            try:
                resp = self.client.v2_management_grade_manager_delete_group(path_params=path_params)
            except APIGatewayResponseError as e:
                raise BKIAMGatewayServiceError(f"delete user group error, group_id: {group_id}, detail: {e}")

            if resp.get("code") != 0:
                logger.exception("delete user group error, group_id: {}, message:{}".format(group_id, resp["message"]))
                raise BKIAMApiError(resp["message"])

    def fetch_user_group_members(self, user_group_id: int) -> List[str]:
        """
        获取某个用户组成员信息

        :param user_group_id: 用户组 ID
        :returns: 用户组成员列表 [{'type': 'user', 'id': 'username', 'expired_at': 1619587562}]
        """
        path_params = {"system_id": settings.IAM_PLUGINS_CENTER_SYSTEM_ID, "group_id": user_group_id}
        params = {"page": DEFAULT_PAGE, "page_size": FETCH_USER_GROUP_MEMBERS_LIMIT}

        try:
            resp = self.client.v2_management_group_members(path_params=path_params, params=params)
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f"get user group members error, detail: {e}")

        if resp.get("code") != 0:
            logger.exception(
                "get user group members error, message:{} \n id: {}, params: {}".format(
                    resp["message"], user_group_id, params
                )
            )
            raise BKIAMApiError(resp["message"])

        return [item["id"] for item in resp["data"]["results"] if item["type"] == "user"]

    def add_user_group_members(self, user_group_id: int, usernames: List[str], expired_after_days: int):
        """
        向某个用户组添加成员

        :param user_group_id: 用户组 ID
        :param usernames: 待添加成员名称
        :param expired_after_days: X 天后权限过期（-1 表示永不过期）
        """
        path_params = {"system_id": settings.IAM_PLUGINS_CENTER_SYSTEM_ID, "group_id": user_group_id}
        data = {
            "members": [{"type": "user", "id": username} for username in usernames],
            "expired_at": calc_expired_at(expired_after_days),
        }

        try:
            resp = self.client.v2_management_add_group_members(path_params=path_params, data=data)
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f"add user group (id: {user_group_id}) members error, detail: {e}")

        if resp.get("code") != 0:
            logger.exception(
                "add user group members error, message:{} \n id: {}, data: {}".format(
                    resp["message"], user_group_id, data
                )
            )
            raise BKIAMApiError(resp["message"])

    def delete_user_group_members(self, user_group_id: int, usernames: List[str]):
        """
        删除某个用户组的成员

        :param user_group_id: 分级管理员 ID
        :param usernames: 待删除的成员名称
        """
        path_params = {"system_id": settings.IAM_PLUGINS_CENTER_SYSTEM_ID, "group_id": user_group_id}
        params = {"type": "user", "ids": ",".join(usernames)}

        try:
            resp = self.client.v2_management_delete_group_members(path_params=path_params, params=params)
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f"delete user group (id: {user_group_id}) members error, detail: {e}")

        if resp.get("code") != 0:
            logger.exception(
                "delete user group members error, message:{} \n id: {}, params: {}".format(
                    resp["message"], user_group_id, params
                )
            )
            raise BKIAMApiError(resp["message"])

    def initial_user_group_policies(
        self,
        plugin_resource: definitions.PluginIAMResource,
        groups: List[definitions.PluginUserGroup],
    ):
        """初始化用户组权限(绑定操作集合)
        为默认的用户组授权

        :param plugin_resource: 蓝鲸插件
        :param groups: 用户组信息
        """
        for group in groups:
            path_params = {"system_id": settings.IAM_PLUGINS_CENTER_SYSTEM_ID, "group_id": group.id}
            data = {
                "actions": [{"id": action} for action in PluginPermissionActions.get_choices_by_role(group.role)],
                "resources": [
                    {
                        "system": settings.IAM_PLUGINS_CENTER_SYSTEM_ID,
                        "type": ResourceType.PLUGIN,
                        "paths": [
                            [
                                {
                                    "system": settings.IAM_PLUGINS_CENTER_SYSTEM_ID,
                                    "type": ResourceType.PLUGIN,
                                    "id": plugin_resource.id,
                                    "name": plugin_resource.name,
                                }
                            ]
                        ],
                    }
                ],
            }

            try:
                resp = self.client.v2_management_groups_policies_grant(path_params=path_params, data=data)
            except APIGatewayResponseError as e:
                raise BKIAMGatewayServiceError(f"grant user groups policies error, detail: {e}")

            if resp.get("code") != 0:
                logger.exception(
                    "grant user groups policies error, message:{} \n user_group_id: {}, data: {}".format(
                        resp["message"], group.id, data
                    )
                )
                raise BKIAMApiError(resp["message"])


lazy_iam_client: BKIAMClient = SimpleLazyObject(BKIAMClient)
