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

from django.db import migrations
from paasng.platform.applications.constants import ApplicationType


def forwards(apps, schema_editor):
    """Find all applications with engine disabled, update their 'type' property to make data consistent"""
    ApplicationEnvironment = apps.get_model('applications', 'ApplicationEnvironment')
    apps_with_envs = set(ApplicationEnvironment.objects.all().values_list('application_id', flat=True))

    Application = apps.get_model('applications', 'Application')
    # All deleted application was considered as "DEFAULT" type, because we don't have sufficient data
    # to get the type of application when all related data was destroyed.
    for app in Application.objects.filter(is_deleted=False):
        if app.id in apps_with_envs:
            continue

        print(f'Found engineless app, id="{app.id}"')
        app.type = ApplicationType.ENGINELESS_APP.value
        app.save(update_fields=['type'])


class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(forwards),
    ]

    dependencies = [
        ('applications', '0003_auto_20210809_1610'),
    ]
