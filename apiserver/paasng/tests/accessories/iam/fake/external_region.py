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
from tests.accessories.iam.permissions import roles


class FakeExternalRegionIAM:
    def is_allowed(self, request: Request) -> bool:
        return request.subject.id in [roles.ADMIN_USER, roles.EXTERNAL_REGION_ENABLED_USER]

    def is_allowed_with_cache(self, request: Request) -> bool:
        return self.is_allowed(request)


class FakeExternalRegionPermission(Permission):
    iam = FakeExternalRegionIAM()

    def resource_inst_multi_actions_allowed(
        self, username: str, action_ids: List[str], resources: List[Resource]
    ) -> Dict[str, bool]:
        if username in [roles.ADMIN_USER, roles.EXTERNAL_REGION_ENABLED_USER]:
            return {action_id: True for action_id in action_ids}

        return {action_id: False for action_id in action_ids}

    def batch_resource_multi_actions_allowed(
        self, username: str, action_ids: List[str], resources: List[Resource]
    ) -> Dict[str, Dict[str, bool]]:

        perms = {}
        for idx, r_id in enumerate([res.id for res in resources]):
            perms[r_id] = {action_id: False for action_id in action_ids}

        return perms
