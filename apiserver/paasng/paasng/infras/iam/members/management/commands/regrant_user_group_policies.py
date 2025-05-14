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

"""Regrant user group policies

Examples:

    # 仅对指定的应用用户组重新授权（支持列表）
    python manage.py regrant_user_group_policies --codes app-code-1 app-code-2 --role developer

    # 对全量应用用户组重新授权
    python manage.py regrant_user_group_policies --all --role operator
"""

import logging
from typing import Dict

from django.core.management.base import BaseCommand
from django.db.models import QuerySet

from paasng.infras.iam.client import BKIAMClient
from paasng.infras.iam.members.models import ApplicationUserGroup
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.platform.applications.constants import ApplicationRole
from paasng.platform.applications.models import Application
from paasng.platform.applications.tenant import get_tenant_id_for_app

logger = logging.getLogger(__name__)

# 角色字面值与枚举值的映射
ROLE_MAP: Dict[str, ApplicationRole] = {
    "administrator": ApplicationRole.ADMINISTRATOR,
    "developer": ApplicationRole.DEVELOPER,
    "operator": ApplicationRole.OPERATOR,
}


class Command(BaseCommand):
    help = "Regrant application iam user group policies"

    def add_arguments(self, parser):
        parser.add_argument("--codes", dest="app_codes", default=[], nargs="*", help="应用 Code 列表")
        parser.add_argument("--all", dest="regrant_all", default=False, action="store_true", help="全量应用")
        parser.add_argument("--role", dest="role", help="授权角色")

    def handle(self, app_codes, regrant_all, role, *args, **options):
        if not (regrant_all or app_codes):
            raise ValueError("please specify --codes or --all")

        if role not in ROLE_MAP:
            raise ValueError("invalid role: %s" % role)

        apps = Application.objects.filter(code__in=app_codes) if app_codes else Application.objects.all()
        self._regrant_user_group_policies(apps, ROLE_MAP[role])

    def _regrant_user_group_policies(self, apps: QuerySet[Application], role: ApplicationRole):
        app_code_name_map = dict(apps.values_list("code", "name"))
        groups = ApplicationUserGroup.objects.filter(app_code__in=app_code_name_map.keys(), role=role)

        total = groups.count()
        regrant_failed_app_codes = set()

        for idx, group in enumerate(groups, start=1):
            print(
                f"regrant app code {group.app_code} role {ApplicationRole(role).name} "
                + f"iam user group: {group.user_group_id} ({idx}/{total})"
            )
            tenant_id = get_tenant_id_for_app(group.app_code)
            iam_client = BKIAMClient(tenant_id)
            try:
                # 先回收用户组所有权限，再重新授权
                iam_client.revoke_user_group_policies(group.user_group_id, list(AppAction.get_values()))
                iam_client.grant_user_group_policies(
                    group.app_code,
                    app_code_name_map[group.app_code],
                    [{"id": group.user_group_id, "role": group.role}],
                )
            except Exception as e:
                print(f"regrant app code {group.app_code} role {ApplicationRole(role).name} iam user group error: {e}")
                regrant_failed_app_codes.add(group.app_code)

        if regrant_failed_app_codes:
            print(f"regrant failed app codes: {regrant_failed_app_codes}")
