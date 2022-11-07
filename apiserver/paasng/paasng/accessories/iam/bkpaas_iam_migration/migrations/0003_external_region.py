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
from django.db import migrations

from paasng.accessories.iam.bkpaas_iam_migration.migrator import BKPaaSIAMMigrator
from paasng.platform.region.models import get_all_regions


def forward_func(apps, schema_editor):
    # 若 Region tencent 不存在，可不注册以下权限
    if 'tencent' not in get_all_regions():
        return

    migrator = BKPaaSIAMMigrator(Migration.migration_json)
    migrator.migrate()


class Migration(migrations.Migration):
    migration_json = "0003_external_region.json"

    dependencies = [('bkpaas_iam_migration', '0002_application')]

    operations = [migrations.RunPython(forward_func)]
