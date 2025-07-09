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

import json
from copy import deepcopy
from pathlib import Path
from typing import Dict

from django.conf import settings
from django.db.migrations import RunPython
from iam.contrib.iam_migration import exceptions
from iam.contrib.iam_migration.utils import do_migrate

from paasng.core.tenant.user import get_init_tenant_id
from paasng.utils import safe_jinja2


class IAMPermissionTemplateRender:
    """TemplateRender used to render jinja2 template located at 'permission-templates'"""

    def __init__(self, template_str: str):
        self.template_str = template_str

    def render(self) -> Dict:
        data_str = safe_jinja2.Template(self.template_str).render(self.context)
        try:
            data = json.loads(data_str)
        except Exception as e:
            raise ValueError(f"{self.template_str} is not a valid json") from e
        if not isinstance(data, dict):
            raise ValueError(f"{self.template_str} is not a valid dict")  # noqa: TRY004
        if "system_id" not in data or "operations" not in data:
            raise ValueError(f"{self.template_str} is not a valid IAM migrations data")
        return data

    @property
    def context(self) -> Dict:
        return {
            "IAM_PLUGINS_CENTER_SYSTEM_ID": settings.IAM_PLUGINS_CENTER_SYSTEM_ID,
            "IAM_RESOURCE_API_HOST": settings.BK_IAM_RESOURCE_API_HOST,
            "CLIENT_APP_CODE": settings.BK_APP_CODE,
        }


class IAMMigrator:
    """A client run iam migration script"""

    def __init__(self, migration_data: Dict):
        self.migration_data = deepcopy(migration_data)

    def migrate(self):
        app_code = settings.IAM_APP_CODE
        app_secret = settings.IAM_APP_SECRET

        iam_host = getattr(settings, "BK_IAM_APIGATEWAY_URL", "")
        if iam_host == "":
            raise exceptions.MigrationFailError("settings.BK_IAM_APIGATEWAY_URL should be set")

        if getattr(settings, "BK_IAM_SKIP", False):
            return

        ok, _ = do_migrate.api_ping(iam_host)
        if not ok:
            raise exceptions.NetworkUnreachableError("bk iam ping error")

        ok = do_migrate.do_migrate(
            self.migration_data, iam_host, app_code, app_secret, bk_tenant_id=get_init_tenant_id()
        )
        if not ok:
            raise exceptions.MigrationFailError("iam migrate fail")


def make_migrate_operation(template_path: Path):
    """wrap IAM migration operation as django migration steps"""
    render = IAMPermissionTemplateRender(template_path.read_text())
    migrator = IAMMigrator(render.render())

    def operation(apps, schema_editor):
        migrator.migrate()

    return RunPython(code=operation)
