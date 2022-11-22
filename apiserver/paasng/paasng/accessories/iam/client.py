# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making BlueKing - PaaS System available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
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
from typing import Dict, List

from bkapi_client_core.exceptions import APIGatewayResponseError
from django.conf import settings

from paasng.accessories.iam.apigw.client import Client
from paasng.accessories.iam.apigw.client import Group as BKIAMGroup
from paasng.accessories.iam.exceptions import BKIAMApiError, BKIAMGatewayServiceError
from paasng.platform.applications.constants import ApplicationRole

from . import utils
from .constants import (
    APP_DEFAULT_ROLES,
    DEFAULT_PAGE,
    FETCH_USER_GROUP_MEMBERS_LIMIT,
    LIST_GRADE_MANAGERS_LIMIT,
    IAMErrorCodes,
    ResourceType,
)

logger = logging.getLogger(__name__)


class BKIAMClient:
    """bk-iam 通过 APIGW 提供的 API"""

    def __init__(self):
        self.client: BKIAMGroup = Client(
            endpoint=settings.BK_API_URL_TMPL, stage=settings.BK_IAM_APIGW_SERVICE_STAGE
        ).api

    def _prepare_headers(self) -> dict:
        headers = {
            'x-bkapi-authorization': json.dumps(
                {
                    'bk_app_code': settings.BK_APP_CODE,
                    'bk_app_secret': settings.BK_APP_SECRET,
                }
            )
        }
        return headers

    def create_grade_managers(self, app_code: str, app_name: str, creator: str) -> int:
        """
        在权限中心上为应用注册分级管理员，若已存在，则返回

        :param app_code: 蓝鲸应用 ID
        :param app_name: 蓝鲸应用名称
        :param creator: 创建人用户名，如 admin
        :returns: 分级管理员 ID
        """
        data = {
            'system': settings.IAM_PAAS_V3_SYSTEM_ID,
            'name': utils.gen_grade_member_name(app_code),
            'description': utils.gen_grade_member_desc(app_code),
            'members': [creator],
            # 仅可对指定的单个应用授权
            'authorization_scopes': [
                {
                    'system': settings.IAM_PAAS_V3_SYSTEM_ID,
                    'actions': [
                        {'id': action} for action in utils.get_app_actions_by_role(ApplicationRole.ADMINISTRATOR)
                    ],
                    'resources': [
                        {
                            'system': settings.IAM_PAAS_V3_SYSTEM_ID,
                            'type': ResourceType.Application,
                            'paths': [
                                [
                                    {
                                        'system': settings.IAM_PAAS_V3_SYSTEM_ID,
                                        'type': ResourceType.Application,
                                        'id': app_code,
                                        'name': app_name,
                                    }
                                ]
                            ],
                        }
                    ],
                }
            ],
            # 可授权的人员范围为公司任意人
            'subject_scopes': [
                {
                    'type': '*',
                    'id': '*',
                }
            ],
        }

        try:
            resp = self.client.management_grade_managers(
                headers=self._prepare_headers(),
                data=data,
            )
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f'create grade managers error, detail: {e}')

        if resp.get('code') != 0:
            if resp['code'] == IAMErrorCodes.CONFLICT:
                return self.fetch_grade_manager(app_code)

            logger.exception(f"create iam grade managers error, message:{resp['message']} \n data: {data}")
            raise BKIAMApiError(resp['message'], resp['code'])

        return resp['data']['id']

    def fetch_grade_manager(self, app_code: str) -> int:
        """
        根据名称查询分级管理员 ID
        # TODO 权限中心 API 支持按名称过滤后，添加名称参数而不是拉回全量数据过滤

        :param app_code: 蓝鲸应用 ID
        :returns: 分级管理员 ID
        """
        try:
            resp = self.client.management_grade_managers_list(
                headers=self._prepare_headers(),
                params={
                    'system': settings.IAM_PAAS_V3_SYSTEM_ID,
                    'page': DEFAULT_PAGE,
                    'page_size': LIST_GRADE_MANAGERS_LIMIT,
                },
            )
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f'fetch grade managers error, detail: {e}')

        if resp.get('code') != 0:
            logger.exception(f"fetch iam grade managers error, message:{resp['message']}")
            raise BKIAMApiError(resp['message'], resp['code'])

        manager_name = utils.gen_grade_member_name(app_code)
        for manager in resp['data']['results']:
            if manager['name'] == manager_name:
                return manager['id']

        raise BKIAMApiError(f'failed to find application [{app_code}] grade manager')

    def fetch_grade_manager_members(self, grade_manager_id: int) -> List[str]:
        """
        获取某个分级管理员的成员列表

        :param grade_manager_id: 分级管理员 ID
        :returns: 分级管理员成员列表
        """
        try:
            resp = self.client.management_grade_manager_members(
                headers=self._prepare_headers(),
                path_params={'id': grade_manager_id},
            )
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f'get grade manager members error, detail: {e}')

        if resp.get('code') != 0:
            logger.exception(
                'get grade manager members error, grade_manager_id: {}, message:{}'.format(
                    grade_manager_id, resp['message']
                )
            )
            raise BKIAMApiError(resp['message'], resp['code'])

        return resp.get('data', [])

    def add_grade_manager_members(self, grade_manager_id: int, usernames: List[str]):
        """
        向某个分级管理员添加成员（分级管理员没有过期时间）

        :param grade_manager_id: 分级管理员 ID
        :param usernames: 待添加成员名称
        """
        path_params, data = {'id': grade_manager_id}, {'members': usernames}

        try:
            resp = self.client.management_add_grade_manager_members(
                headers=self._prepare_headers(),
                path_params=path_params,
                data=data,
            )
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f'add grade manager (id: {grade_manager_id}) members error, detail: {e}')

        if resp.get('code') != 0:
            logger.exception(
                'add grade manager (id: {}) members error, message:{} \n data: {}'.format(
                    grade_manager_id, resp['message'], data
                )
            )
            raise BKIAMApiError(resp['message'], resp['code'])

    def delete_grade_manager_members(self, grade_manager_id: int, usernames: List[str]):
        """
        删除某个分级管理员的成员

        :param grade_manager_id: 分级管理员 ID
        :param usernames: 待删除的成员名称
        """
        path_params, params = {'id': grade_manager_id}, {'members': ','.join(usernames)}

        try:
            resp = self.client.management_delete_grade_manager_members(
                headers=self._prepare_headers(),
                path_params=path_params,
                params=params,
            )
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f'delete grade manager (id: {grade_manager_id}) members error, detail: {e}')

        if resp.get('code') != 0:
            logger.exception(
                'delete grade manager members error, message:{} \n id: {}, params: {}'.format(
                    resp['message'], grade_manager_id, params
                )
            )
            raise BKIAMApiError(resp['message'], resp['code'])

    def create_builtin_user_groups(self, grade_manager_id: int, app_code: str) -> List[Dict]:
        """
        为单个应用创建用户组（默认3个：管理员，开发者，运营者）

        :param grade_manager_id: 分级管理员 ID
        :param app_code: 蓝鲸应用 ID
        :returns: 用户组信息
        """
        path_params = {'system_id': settings.IAM_PAAS_V3_SYSTEM_ID, 'id': grade_manager_id}

        groups = [
            {
                'name': utils.gen_user_group_name(app_code, role),
                'description': utils.gen_user_group_desc(app_code, role),
                # 只读用户组，设置为 True 后，分级管理员无法在权限中心产品上删除该用户组
                'readonly': True,
            }
            for role in APP_DEFAULT_ROLES
        ]
        data = {'groups': groups}

        try:
            resp = self.client.v2_management_grade_manager_create_groups(
                headers=self._prepare_headers(),
                path_params=path_params,
                data=data,
            )
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f'create user groups error, detail: {e}')

        if resp.get('code') != 0:
            logger.exception(
                'create user groups error, message:{} \n grade_manager_id: {}, data: {}'.format(
                    resp['message'], grade_manager_id, data
                )
            )
            raise BKIAMApiError(resp['message'], resp['code'])

        # 按照顺序，填充申请创建得到的各个用户组的 ID
        user_group_ids = resp.get('data', [])
        for group, user_group_id, role in zip(groups, user_group_ids, APP_DEFAULT_ROLES):
            group.update({"id": user_group_id, "role": role})  # type: ignore
        return groups

    def delete_user_groups(self, user_group_ids: List[int]):
        """删除指定的用户组"""
        for group_id in user_group_ids:
            path_params = {'system_id': settings.IAM_PAAS_V3_SYSTEM_ID, 'group_id': group_id}
            try:
                resp = self.client.v2_management_grade_manager_delete_group(
                    headers=self._prepare_headers(),
                    path_params=path_params,
                )
            except APIGatewayResponseError as e:
                raise BKIAMGatewayServiceError(f'delete user group error, group_id: {group_id}, detail: {e}')

            if resp.get('code') != 0:
                logger.exception('delete user group error, group_id: {}, message:{}'.format(group_id, resp['message']))
                raise BKIAMApiError(resp['message'], resp['code'])

    def fetch_user_group_members(self, user_group_id: int) -> List[str]:
        """
        获取某个用户组成员信息

        :param user_group_id: 用户组 ID
        :returns: 用户组成员列表 ['username1', 'username2']
        """
        path_params = {'system_id': settings.IAM_PAAS_V3_SYSTEM_ID, 'group_id': user_group_id}
        params = {'page': DEFAULT_PAGE, 'page_size': FETCH_USER_GROUP_MEMBERS_LIMIT}

        try:
            resp = self.client.v2_management_group_members(
                headers=self._prepare_headers(), path_params=path_params, params=params
            )
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f'get user group members error, detail: {e}')

        if resp.get('code') != 0:
            logger.exception(
                'get user group members error, message:{} \n id: {}, params: {}'.format(
                    resp['message'], user_group_id, params
                )
            )
            raise BKIAMApiError(resp['message'], resp['code'])

        return [user['id'] for user in resp['data']['results']]

    def add_user_group_members(self, user_group_id: int, usernames: List[str], expired_after_days: int):
        """
        向某个用户组添加成员

        :param user_group_id: 用户组 ID
        :param usernames: 待添加成员名称
        :param expired_after_days: X 天后权限过期（-1 表示永不过期）
        """
        path_params = {'system_id': settings.IAM_PAAS_V3_SYSTEM_ID, 'group_id': user_group_id}
        data = {
            'members': [{'type': 'user', 'id': username} for username in usernames],
            'expired_at': utils.calc_expired_at(expired_after_days),
        }

        try:
            resp = self.client.v2_management_add_group_members(
                headers=self._prepare_headers(),
                path_params=path_params,
                data=data,
            )
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f'add user group (id: {user_group_id}) members error, detail: {e}')

        if resp.get('code') != 0:
            logger.exception(
                'add user group members error, message:{} \n id: {}, data: {}'.format(
                    resp['message'], user_group_id, data
                )
            )
            raise BKIAMApiError(resp['message'], resp['code'])

    def delete_user_group_members(self, user_group_id: int, usernames: List[str]):
        """
        删除某个用户组的成员

        :param user_group_id: 分级管理员 ID
        :param usernames: 待删除的成员名称
        """
        path_params = {'system_id': settings.IAM_PAAS_V3_SYSTEM_ID, 'group_id': user_group_id}
        params = {'type': 'user', 'ids': ','.join(usernames)}

        try:
            resp = self.client.v2_management_delete_group_members(
                headers=self._prepare_headers(),
                path_params=path_params,
                params=params,
            )
        except APIGatewayResponseError as e:
            raise BKIAMGatewayServiceError(f'delete user group (id: {user_group_id}) members error, detail: {e}')

        if resp.get('code') != 0:
            logger.exception(
                'delete user group members error, message:{} \n id: {}, params: {}'.format(
                    resp['message'], user_group_id, params
                )
            )
            raise BKIAMApiError(resp['message'], resp['code'])

    def grant_user_group_policies(self, app_code: str, app_name: str, groups: List[Dict]):
        """
        为默认的用户组授权

        :param app_code: 蓝鲸应用 ID
        :param app_name: 蓝鲸应用名称
        :param groups: 用户组信息（create_builtin_user_groups 返回结果）
        """
        for group in groups:
            path_params = {'system_id': settings.IAM_PAAS_V3_SYSTEM_ID, 'group_id': group['id']}

            data = {
                'actions': [{'id': action} for action in utils.get_app_actions_by_role(group['role'])],
                'resources': [
                    {
                        'system': settings.IAM_PAAS_V3_SYSTEM_ID,
                        'type': ResourceType.Application,
                        'paths': [
                            [
                                {
                                    'system': settings.IAM_PAAS_V3_SYSTEM_ID,
                                    'type': ResourceType.Application,
                                    'id': app_code,
                                    'name': app_name,
                                }
                            ]
                        ],
                    }
                ],
            }

            try:
                resp = self.client.v2_management_groups_policies_grant(
                    headers=self._prepare_headers(),
                    path_params=path_params,
                    data=data,
                )
            except APIGatewayResponseError as e:
                raise BKIAMGatewayServiceError(f'grant user groups policies error, detail: {e}')

            if resp.get('code') != 0:
                logger.exception(
                    'grant user groups policies error, message:{} \n user_group_id: {}, data: {}'.format(
                        resp['message'], group['id'], data
                    )
                )
                raise BKIAMApiError(resp['message'], resp['code'])
