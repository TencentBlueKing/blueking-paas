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
from typing import List

from django.db import transaction
from django.db.models import QuerySet

from paasng.platform.applications.constants import ApplicationRole
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.environments.exceptions import RoleNotAllowError
from paasng.platform.environments.models import EnvRoleProtection
from paasng.platform.modules.models.module import Module


def env_role_protection_check(operation: str, env: ModuleEnvironment, roles: List[ApplicationRole]):
    """检查是否存在环境保护"""
    protections = EnvRoleProtection.objects.filter(operation=operation, module_env=env)

    # 未开启任何保护
    if not protections.exists():
        return

    # 取交集，如果结果不为空，则说明有允许的角色
    if set(roles) & set(protections.values_list("allowed_role", flat=True)):
        return

    raise RoleNotAllowError()


@transaction.atomic
def batch_save_protections(
    module: Module, operation: str, allowed_roles: list, input_envs: list
) -> QuerySet[EnvRoleProtection]:
    qs = EnvRoleProtection.objects.filter(
        module_env__module=module, operation=operation, allowed_role__in=allowed_roles
    )
    # 查看 DB 中已经设置了操作限制的环境
    db_envs_set = set(qs.values_list("module_env__environment", flat=True))

    # 不再输入数据中，但是在 DB 中的环境，则需要删除
    input_envs_set = set(input_envs)
    delete_envs = db_envs_set.difference(input_envs_set)
    qs.filter(module_env__environment__in=delete_envs).delete()

    # 在输入数据中，但是不在 DB 中环境，则需要新建
    create_envs = input_envs_set.difference(db_envs_set)
    protections = []
    for _env in create_envs:
        module_env = module.get_envs(_env)
        for role in allowed_roles:
            protections.append(EnvRoleProtection(module_env=module_env, operation=operation, allowed_role=role))

    EnvRoleProtection.objects.bulk_create(protections)

    return qs
