# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import json
import logging
from typing import Dict, List, Optional

from bkapi_client_core.exceptions import APIGatewayResponseError, HTTPResponseError
from django.conf import settings

from paasng.infras.iam import utils
from paasng.infras.iam.apigw.client import Client
from paasng.infras.iam.apigw.client import Group as BKIAMGroup
from paasng.infras.iam.constants import (
    APP_DEFAULT_ROLES,
    BK_LOG_SYSTEM_ID,
    BK_MONITOR_SYSTEM_ID,
    DEFAULT_PAGE,
    FETCH_USER_GROUP_MEMBERS_LIMIT,
    LIST_GRADE_MANAGERS_LIMIT,
    IAMErrorCodes,
)
from paasng.infras.iam.exceptions import BKIAMApiError, BKIAMGatewayServiceError
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.platform.applications.constants import ApplicationRole

logger = logging.getLogger(__name__)


class BKIAMClient:
    """bk-iam 通过 APIGW 提供的 API"""

    def __init__(self):
        self._client = Client(endpoint=settings.BK_API_URL_TMPL, stage=settings.BK_IAM_APIGW_SERVICE_STAGE)
        self._client.update_headers(self._prepare_headers())
        self.client: BKIAMGroup = self._client.api

    def _prepare_headers(self) -> dict:
        headers = {
            "x-bkapi-authorization": json.dumps(
                {
                    "bk_app_code": settings.BK_APP_CODE,
                    "bk_app_secret": settings.BK_APP_SECRET,
                }
            )
        }
        return headers

    def create_grade_managers(self, app_code: str, app_name: str, init_member: Optional[str] = None) -> int:
        """
        在权限中心上为应用注册分级管理员，若已存在，则返回

        :param app_code: 蓝鲸应用 ID
        :param app_name: 蓝鲸应用名称
        :param init_member: 初始分级管理员用户名，如 admin，若为空值，则该用户组没有分级管理员
        :returns: 分级管理员 ID
        """
        data = {
            "system": settings.IAM_PAAS_V3_SYSTEM_ID,
            "name": utils.gen_grade_manager_name(app_code),
            "description": utils.gen_grade_manager_desc(app_code),
            "members": [init_member] if init_member else [],
            # 创建分级管理员时，仅授权开发者中心的权限
            "authorization_scopes": [
                utils.get_paas_authorization_scopes(
                    app_code, app_name, ApplicationRole.ADMINISTRATOR, include_system=True
                )
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
            resp = self.client.management_grade_managers(
                data=data,
            )
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f"create grade managers error, detail: {e}")

        if resp.get("code") != 0:
            if resp["code"] == IAMErrorCodes.CONFLICT:
                return self.fetch_grade_manager(app_code)

            logger.exception(f"create iam grade managers error, message:{resp['message']} \n data: {data}")
            raise BKIAMApiError(resp["message"], resp["code"])

        return resp["data"]["id"]

    def delete_grade_manager(self, grade_manager_id: str):
        """
        删除注册到权限中心的分级管理员

        :param grade_manager_id: 分级管理员 ID
        """
        path_params = {"system_id": settings.IAM_PAAS_V3_SYSTEM_ID, "id": grade_manager_id}

        try:
            resp = self.client.v2_management_delete_grade_manager(
                path_params=path_params,
            )
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f"delete grade manager error, detail: {e}")

        if resp.get("code") != 0:
            logger.exception(
                "delete grade manager error, message:{} grade_manager_id: {}".format(resp["message"], grade_manager_id)
            )
            raise BKIAMApiError(resp["message"], resp["code"])

    def fetch_grade_manager(self, app_code: str) -> int:
        """
        根据名称查询分级管理员 ID

        :param app_code: 蓝鲸应用 ID
        :returns: 分级管理员 ID
        """
        manager_name = utils.gen_grade_manager_name(app_code)
        try:
            resp = self.client.management_grade_managers_list(
                params={
                    "name": manager_name,
                    "system": settings.IAM_PAAS_V3_SYSTEM_ID,
                    "page": DEFAULT_PAGE,
                    "page_size": LIST_GRADE_MANAGERS_LIMIT,
                },
            )
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f"fetch grade managers error, detail: {e}")

        if resp.get("code") != 0:
            logger.exception(f"fetch iam grade managers error, message:{resp['message']}")
            raise BKIAMApiError(resp["message"], resp["code"])

        for manager in resp["data"]["results"]:
            if manager["name"] == manager_name:
                return manager["id"]

        raise BKIAMApiError(f"failed to find application [{app_code}] grade manager")

    def fetch_grade_manager_members(self, grade_manager_id: int) -> List[str]:
        """
        获取某个分级管理员的成员列表

        :param grade_manager_id: 分级管理员 ID
        :returns: 分级管理员成员列表
        """
        try:
            resp = self.client.management_grade_manager_members(
                path_params={"id": grade_manager_id},
            )
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f"get grade manager members error, detail: {e}")

        if resp.get("code") != 0:
            logger.exception(
                "get grade manager members error, grade_manager_id: {}, message:{}".format(
                    grade_manager_id, resp["message"]
                )
            )
            raise BKIAMApiError(resp["message"], resp["code"])

        return resp.get("data", [])

    def add_grade_manager_members(self, grade_manager_id: int, usernames: List[str]):
        """
        向某个分级管理员添加成员（分级管理员没有过期时间）

        :param grade_manager_id: 分级管理员 ID
        :param usernames: 待添加成员名称
        """
        # admin 用户拥有全量权限，不应占用配额也不需要授权
        usernames = [u for u in usernames if u != settings.ADMIN_USERNAME]
        if not usernames:
            return

        path_params, data = {"id": grade_manager_id}, {"members": usernames}

        try:
            resp = self.client.management_add_grade_manager_members(
                path_params=path_params,
                data=data,
            )
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f"add grade manager (id: {grade_manager_id}) members error, detail: {e}")

        if resp.get("code") != 0:
            logger.exception(
                "add grade manager (id: {}) members error, message:{} \n data: {}".format(
                    grade_manager_id, resp["message"], data
                )
            )
            raise BKIAMApiError(resp["message"], resp["code"])

    def delete_grade_manager_members(self, grade_manager_id: int, usernames: List[str]):
        """
        删除某个分级管理员的成员

        :param grade_manager_id: 分级管理员 ID
        :param usernames: 待删除的成员名称
        """
        path_params, params = {"id": grade_manager_id}, {"members": ",".join(usernames)}

        try:
            resp = self.client.management_delete_grade_manager_members(
                path_params=path_params,
                params=params,
            )
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f"delete grade manager (id: {grade_manager_id}) members error, detail: {e}")

        if resp.get("code") != 0:
            logger.exception(
                "delete grade manager members error, message:{} \n id: {}, params: {}".format(
                    resp["message"], grade_manager_id, params
                )
            )
            raise BKIAMApiError(resp["message"], resp["code"])

    def create_builtin_user_groups(self, grade_manager_id: int, app_code: str) -> List[Dict]:
        """
        为单个应用创建用户组（默认3个：管理员，开发者，运营者）

        :param grade_manager_id: 分级管理员 ID
        :param app_code: 蓝鲸应用 ID
        :returns: 用户组信息
        """
        path_params = {"system_id": settings.IAM_PAAS_V3_SYSTEM_ID, "id": grade_manager_id}

        groups = [
            {
                "name": utils.gen_user_group_name(app_code, role),
                "description": utils.gen_user_group_desc(app_code, role),
                # 只读用户组，设置为 True 后，分级管理员无法在权限中心产品上删除该用户组
                "readonly": True,
            }
            for role in APP_DEFAULT_ROLES
        ]
        data = {"groups": groups}

        conflict = False
        try:
            resp = self.client.v2_management_grade_manager_create_groups(
                path_params=path_params,
                data=data,
            )
        except HTTPResponseError as e:
            if e.response.status_code != 409:
                raise BKIAMGatewayServiceError(f"create user groups error, detail: {e}")
            conflict = True
            resp = self.client.v2_management_grade_manager_list_groups(path_params=path_params)
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f"create user groups error, detail: {e}")

        if resp.get("code") != 0:
            logger.exception(
                "create user groups error, message:{} \n grade_manager_id: {}, data: {}".format(
                    resp["message"], grade_manager_id, data
                )
            )
            raise BKIAMApiError(resp["message"], resp["code"])

        if conflict:
            all_groups = {group["name"]: group for group in resp["data"]["results"]}
            return [
                {**all_groups[expected_group["name"]], "role": role}
                for expected_group, role in zip(groups, APP_DEFAULT_ROLES)
            ]

        # 按照顺序，填充申请创建得到的各个用户组的 ID
        user_group_ids = resp.get("data", [])
        for group, user_group_id, role in zip(groups, user_group_ids, APP_DEFAULT_ROLES):
            group.update({"id": user_group_id, "role": role})  # type: ignore
        return groups

    def delete_user_groups(self, user_group_ids: List[int]):
        """删除指定的用户组"""
        for group_id in user_group_ids:
            path_params = {"system_id": settings.IAM_PAAS_V3_SYSTEM_ID, "group_id": group_id}
            try:
                resp = self.client.v2_management_grade_manager_delete_group(
                    path_params=path_params,
                )
            except APIGatewayResponseError as e:
                raise BKIAMGatewayServiceError(f"delete user group error, group_id: {group_id}, detail: {e}")

            if resp.get("code") != 0:
                logger.exception("delete user group error, group_id: {}, message:{}".format(group_id, resp["message"]))
                raise BKIAMApiError(resp["message"], resp["code"])

    def fetch_user_group_members(self, user_group_id: int) -> List[str]:
        """
        获取某个用户组成员信息

        :param user_group_id: 用户组 ID
        :returns: 用户组成员列表 ['username1', 'username2']
        """
        path_params = {"system_id": settings.IAM_PAAS_V3_SYSTEM_ID, "group_id": user_group_id}
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
            raise BKIAMApiError(resp["message"], resp["code"])

        return [user["id"] for user in resp["data"]["results"]]

    def add_user_group_members(self, user_group_id: int, usernames: List[str], expired_after_days: int):
        """
        向某个用户组添加成员

        :param user_group_id: 用户组 ID
        :param usernames: 待添加成员名称
        :param expired_after_days: X 天后权限过期（-1 表示永不过期）
        """
        # admin 用户拥有全量权限，不应占用配额也不需要授权
        usernames = [u for u in usernames if u != settings.ADMIN_USERNAME]
        if not usernames:
            return

        path_params = {"system_id": settings.IAM_PAAS_V3_SYSTEM_ID, "group_id": user_group_id}
        data = {
            "members": [{"type": "user", "id": username} for username in usernames],
            "expired_at": utils.calc_expired_at(expired_after_days),
        }

        try:
            resp = self.client.v2_management_add_group_members(
                path_params=path_params,
                data=data,
            )
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f"add user group (id: {user_group_id}) members error, detail: {e}")

        if resp.get("code") != 0:
            logger.exception(
                "add user group members error, message:{} \n id: {}, data: {}".format(
                    resp["message"], user_group_id, data
                )
            )
            raise BKIAMApiError(resp["message"], resp["code"])

    def delete_user_group_members(self, user_group_id: int, usernames: List[str]):
        """
        删除某个用户组的成员

        :param user_group_id: 分级管理员 ID
        :param usernames: 待删除的成员名称
        """
        path_params = {"system_id": settings.IAM_PAAS_V3_SYSTEM_ID, "group_id": user_group_id}
        params = {"type": "user", "ids": ",".join(usernames)}

        try:
            resp = self.client.v2_management_delete_group_members(
                path_params=path_params,
                params=params,
            )
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f"delete user group (id: {user_group_id}) members error, detail: {e}")

        if resp.get("code") != 0:
            logger.exception(
                "delete user group members error, message:{} \n id: {}, params: {}".format(
                    resp["message"], user_group_id, params
                )
            )
            raise BKIAMApiError(resp["message"], resp["code"])

    def grant_user_group_policies(self, app_code: str, app_name: str, groups: List[Dict]):
        """
        为默认的用户组授权

        :param app_code: 蓝鲸应用 ID
        :param app_name: 蓝鲸应用名称
        :param groups: 用户组信息（create_builtin_user_groups 返回结果）
        """
        for group in groups:
            path_params = {"system_id": settings.IAM_PAAS_V3_SYSTEM_ID, "group_id": group["id"]}
            data = utils.get_paas_authorization_scopes(app_code, app_name, group["role"])

            try:
                resp = self.client.v2_management_groups_policies_grant(
                    path_params=path_params,
                    data=data,
                )
            except APIGatewayResponseError as e:
                raise BKIAMGatewayServiceError(f"grant user groups policies error, detail: {e}")

            if resp.get("code") != 0:
                logger.exception(
                    "grant user groups policies error, message:{} \n user_group_id: {}, data: {}".format(
                        resp["message"], group["id"], data
                    )
                )
                raise BKIAMApiError(resp["message"], resp["code"])

    def revoke_user_group_policies(self, user_group_id: int, actions: List[AppAction]):
        """
        回收指定用户组的指定 action 权限
        :param user_group_id: 用户组 ID
        :param actions: 要回收的 action 列表
        """
        path_params = {"system_id": settings.IAM_PAAS_V3_SYSTEM_ID, "group_id": user_group_id}
        data = {"actions": [{"id": action} for action in actions]}

        try:
            resp = self.client.v2_management_groups_policies_revoke_by_action(
                path_params=path_params,
                data=data,
            )
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f"revoke user groups policies error, detail: {e}")

        if resp.get("code") != 0:
            logger.exception(
                "revoke user groups policies error, message:{} \n user_group_id: {}, data: {}".format(
                    resp["message"], user_group_id, data
                )
            )
            raise BKIAMApiError(resp["message"], resp["code"])

    def update_grade_managers_with_bksaas_space(
        self, grade_manager_id: str, app_code: str, app_name: str, bk_space_id: str
    ):
        """
        给分级管理员添加监控、日志空间的授权范围

        :param grade_manager_id: 初始分级管理员ID
        :param app_code: 蓝鲸应用 ID
        :param app_name: 蓝鲸应用名称
        :param bk_space_id: 蓝鲸监控的空间ID，注意这是这一个负数
        """
        data = {
            "system": settings.IAM_PAAS_V3_SYSTEM_ID,
            "name": utils.gen_grade_manager_name(app_code),
            "description": utils.gen_grade_manager_desc(app_code),
            # 除创建时初始化的开发者中心权限外，新增监控平台、日志平台最小空间权限
            "authorization_scopes": [
                utils.get_paas_authorization_scopes(
                    app_code, app_name, ApplicationRole.ADMINISTRATOR, include_system=True
                )
            ]
            + utils.get_bk_monitor_authorization_scope_list(bk_space_id, app_name, include_system=True)
            + utils.get_bk_log_authorization_scope_list(bk_space_id, app_name, include_system=True),
            # 可授权的人员范围为公司任意人
            "subject_scopes": [
                {
                    "type": "*",
                    "id": "*",
                }
            ],
        }

        path_params = {"id": grade_manager_id}
        try:
            resp = self.client.management_grade_managers_update(
                headers=self._prepare_headers(),
                data=data,
                path_params=path_params,
            )
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f"update grade managers error, detail: {e}")

        if resp.get("code") != 0:
            if resp["code"] == IAMErrorCodes.CONFLICT:
                return self.fetch_grade_manager(app_code)

            logger.exception(f"update iam grade managers error, message:{resp['message']} \n data: {data}")
            raise BKIAMApiError(resp["message"], resp["code"])
        return None

    def grant_user_group_policies_in_bk_monitor(self, bk_space_id: str, app_name: str, groups: List[Dict]):
        """
        为默认的用户组添加监控平台的空间权限

        :param bk_space_id: 蓝鲸监控的空间ID，注意这是这一个负数
        :param app_name: 蓝鲸应用名称
        :param groups: 用户组信息（create_builtin_user_groups 返回结果）
        """
        for group in groups:
            path_params = {"system_id": BK_MONITOR_SYSTEM_ID, "group_id": group["id"]}

            scope_list = utils.get_bk_monitor_authorization_scope_list(bk_space_id, app_name)
            for scope in scope_list:
                try:
                    resp = self.client.v2_management_groups_policies_grant(
                        headers=self._prepare_headers(),
                        path_params=path_params,
                        data=scope,
                    )
                except APIGatewayResponseError as e:
                    raise BKIAMGatewayServiceError(f"grant user groups policies in bk monitor  error, detail: {e}")

                if resp.get("code") != 0:
                    logger.exception(
                        "grant user groups policies in bk monitor error, msg:{} \n user_group_id: {}, data: {}".format(
                            resp["message"], group["id"], scope
                        )
                    )
                    raise BKIAMApiError(resp["message"], resp["code"])

    def grant_user_group_policies_in_bk_log(self, bk_space_id: str, app_name: str, groups: List[Dict]):
        """
        为默认的用户组添加蓝鲸日志平台的空间权限

        :param bk_space_id: 蓝鲸监控的空间ID，注意这是这一个负数
        :param app_name: 蓝鲸应用名称
        :param groups: 用户组信息（create_builtin_user_groups 返回结果）
        """
        for group in groups:
            path_params = {"system_id": BK_LOG_SYSTEM_ID, "group_id": group["id"]}

            scope_list = utils.get_bk_log_authorization_scope_list(bk_space_id, app_name)
            for scope in scope_list:
                try:
                    resp = self.client.v2_management_groups_policies_grant(
                        headers=self._prepare_headers(),
                        path_params=path_params,
                        data=scope,
                    )
                except APIGatewayResponseError as e:
                    raise BKIAMGatewayServiceError(f"grant user groups policies in bk log  error, detail: {e}")

                if resp.get("code") != 0:
                    logger.exception(
                        "grant user groups policies in bk log error, message:{} \n user_group_id: {}, data: {}".format(
                            resp["message"], group["id"], scope
                        )
                    )
                    raise BKIAMApiError(resp["message"], resp["code"])
