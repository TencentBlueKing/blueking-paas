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
from typing import Dict, List

from iam import Request, Resource

from paasng.accessories.iam.permissions.perm import Permission
from paasng.accessories.iam.permissions.resources.application import AppAction
from tests.accessories.iam.permissions import roles

app_admin_allowed_actions = AppAction.get_values()

app_develop_allowed_actions = [
    AppAction.VIEW_BASIC_INFO,
    AppAction.DATA_STATISTICS,
    AppAction.BASIC_DEVELOP,
    AppAction.MANAGE_CLOUD_API,
    AppAction.VIEW_ALERT_RECORDS,
    AppAction.EDIT_ALERT_POLICY,
]

app_operate_allowed_actions = [
    AppAction.VIEW_BASIC_INFO,
    AppAction.EDIT_BASIC_INFO,
    AppAction.MANAGE_ACCESS_CONTROL,
    AppAction.MANAGE_APP_MARKET,
    AppAction.DATA_STATISTICS,
    AppAction.VIEW_ALERT_RECORDS,
]


class FakeApplicationIAM:
    def is_allowed(self, request: Request) -> bool:
        if request.subject.id == roles.ADMIN_USER:
            return True
        if request.subject.id == roles.APP_ADMIN_USER and request.action.id in app_admin_allowed_actions:
            return True
        if request.subject.id == roles.APP_DEVELOP_USER and request.action.id in app_develop_allowed_actions:
            return True
        if request.subject.id == roles.APP_OPERATE_USER and request.action.id in app_operate_allowed_actions:
            return True
        return False

    def is_allowed_with_cache(self, request: Request) -> bool:
        return self.is_allowed(request)


class FakeApplicationPermission(Permission):
    iam = FakeApplicationIAM()

    def resource_inst_multi_actions_allowed(
        self, username: str, action_ids: List[str], resources: List[Resource]
    ) -> Dict[str, bool]:
        if username in [roles.ADMIN_USER, roles.APP_ADMIN_USER]:
            return {action_id: True for action_id in action_ids}

        multi = {action_id: False for action_id in action_ids}
        if username == roles.APP_DEVELOP_USER:
            for key in multi:
                if key in app_develop_allowed_actions:
                    multi[key] = True
        elif username == roles.APP_OPERATE_USER:
            for key in multi:
                if key in app_operate_allowed_actions:
                    multi[key] = True
        return multi

    def batch_resource_multi_actions_allowed(
        self, username: str, action_ids: List[str], resources: List[Resource]
    ) -> Dict[str, Dict[str, bool]]:
        perms = {}
        for _, r_id in enumerate([res.id for res in resources]):
            perms[r_id] = {action_id: False for action_id in action_ids}

        return perms
