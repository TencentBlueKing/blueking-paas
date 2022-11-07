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
import pytest

from paasng.platform.applications.constants import ApplicationRole as AR
from paasng.platform.environments.exceptions import RoleNotAllowError
from paasng.platform.environments.models import EnvRoleProtection
from paasng.platform.environments.utils import env_role_protection_check

pytestmark = pytest.mark.django_db


class TestEnvRoleProtectionCheck:
    @pytest.mark.parametrize(
        'db_roles,forbidden_roles,allowed_roles',
        [
            ([], [], [AR.ADMINISTRATOR, AR.DEVELOPER, AR.OPERATOR]),
            ([AR.ADMINISTRATOR], [AR.DEVELOPER, AR.OPERATOR], [AR.ADMINISTRATOR]),
            ([AR.ADMINISTRATOR, AR.DEVELOPER], [AR.OPERATOR], [AR.ADMINISTRATOR, AR.DEVELOPER]),
        ],
    )
    def test_protection(self, bk_prod_env, db_roles, forbidden_roles, allowed_roles):
        for role in db_roles:
            EnvRoleProtection.objects.create(allowed_role=role, module_env=bk_prod_env, operation='deploy')

        for role in forbidden_roles:
            with pytest.raises(RoleNotAllowError):
                env_role_protection_check(operation='deploy', env=bk_prod_env, role=role)

        for role in allowed_roles:
            env_role_protection_check(operation='deploy', env=bk_prod_env, role=role)
