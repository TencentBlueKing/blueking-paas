# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from typing import List

from paasng.platform.applications.constants import ApplicationRole
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.environments.exceptions import RoleNotAllowError
from paasng.platform.environments.models import EnvRoleProtection


def env_role_protection_check(operation: str, env: ModuleEnvironment, roles: List[ApplicationRole]):
    """检查是否存在环境保护"""
    protections = EnvRoleProtection.objects.filter(operation=operation, module_env=env)

    # 未开启任何保护
    if not protections.exists():
        return

    # 取交集，如果结果不为空，则说明有允许的角色
    if set(roles) & set(protections.values_list('allowed_role', flat=True)):
        return

    raise RoleNotAllowError()
