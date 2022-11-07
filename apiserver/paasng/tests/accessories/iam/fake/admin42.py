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
from typing import Dict, List

from iam import Request, Resource

from paasng.accessories.iam.permissions.perm import Permission
from paasng.accessories.iam.permissions.resources.admin42 import Admin42Action
from tests.accessories.iam.permissions import roles


class FakeAdmin42IAM:
    def is_allowed(self, request: Request) -> bool:
        if request.subject.id == roles.ADMIN_USER:
            return True
        if request.subject.id == roles.PLATFORM_ADMIN_USER and request.action.id == Admin42Action.MANAGE_PLATFORM:
            return True
        if request.subject.id == roles.PLATFORM_OPERATE_USER and request.action.id == Admin42Action.OPERATE_PLATFORM:
            return True
        if request.subject.id == roles.APP_TMPL_ADMIN_USER and request.action.id == Admin42Action.MANAGE_APP_TEMPLATES:
            return True
        return False

    def is_allowed_with_cache(self, request: Request) -> bool:
        return self.is_allowed(request)


class FakeAdmin42Permission(Permission):
    iam = FakeAdmin42IAM()

    def resource_inst_multi_actions_allowed(
        self, username: str, action_ids: List[str], resources: List[Resource]
    ) -> Dict[str, bool]:
        if username == roles.ADMIN_USER:
            return {action_id: True for action_id in action_ids}

        multi = {action_id: False for action_id in action_ids}
        if username == roles.PLATFORM_OPERATE_USER:
            if Admin42Action.OPERATE_PLATFORM in multi:
                multi[Admin42Action.OPERATE_PLATFORM] = True
        elif username == roles.APP_TMPL_ADMIN_USER:
            if Admin42Action.MANAGE_APP_TEMPLATES in multi:
                multi[Admin42Action.MANAGE_APP_TEMPLATES] = True

        return multi

    def batch_resource_multi_actions_allowed(
        self, username: str, action_ids: List[str], resources: List[Resource]
    ) -> Dict[str, Dict[str, bool]]:

        perms = {}
        for idx, r_id in enumerate([res.id for res in resources]):
            perms[r_id] = {action_id: False for action_id in action_ids}

        return perms
