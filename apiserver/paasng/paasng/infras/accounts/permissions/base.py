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
from collections import OrderedDict
from typing import Dict, List, Tuple

from paasng.infras.accounts.constants import SiteRole


class ProtectedResource:
    """Resource been protected, it can be referred to anything"""

    permissions: List[Tuple[str, str]] = []

    def __init__(self):
        self.roles = {}
        self.binded_obj_class = None
        self._permissions = OrderedDict()
        for codename, description in self.permissions:
            self._permissions[codename] = Permission(codename, description)

    def has_permission(self, perm_name: str) -> bool:
        """Check if an permission name is valid"""
        return perm_name in self._permissions

    def add_role(self, name: SiteRole, permissions_map: Dict):
        """Add a new role"""
        if set(permissions_map.keys()) != set(self._permissions.keys()):
            raise ValueError(
                'You must provide same permission names when add new role, '
                'did you add a new permission in the Resource?'
            )

        self.roles[name] = ObjectRole(self, name, permissions_map)

    def add_nobody_role(self):
        self.roles[SiteRole.NOBODY] = ObjectNobodyRole()

    def get_role(self, name):
        return self.roles[name]

    def get_role_of_user(self, user, obj):
        return self.get_role(self._get_role_of_user(user, obj))

    def _get_role_of_user(self, user, obj):
        raise NotImplementedError


class Permission:
    def __init__(self, codename, description):
        self.codename = codename
        self.description = description

    def __str__(self):
        return '<Permission %s>' % self.codename


class ObjectRole:
    """Role object"""

    def __init__(self, resource, name, permissions_map):
        self.resource = resource
        self.name = name
        self.permissions_map = permissions_map

    def has_perm(self, action):
        result = self.permissions_map.get(action, None)
        if result is None:
            raise ValueError('"%s" is not a valid action name' % action)
        return result


class ObjectNobodyRole:
    """A special role which has not rights to do anything"""

    name = SiteRole.NOBODY

    def has_perm(self, perm_name):
        return False
