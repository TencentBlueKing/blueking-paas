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

def add_some_res_quota_plans(apps, schema_editor):
    """add some resource quota plans"""
    ResQuotaPlan = apps.get_model("bkapp_model", "ResQuotaPlan")

    need_add_plans = [
        {
            "name": "2C1G",
            "limits": {"cpu": "2000m", "memory": "1024Mi"},
            "requests": {"cpu": "200m", "memory": "256Mi"},
            "is_active": True,
            "is_builtin": True,
        },
        {
            "name": "2C2G",
            "limits": {"cpu": "2000m", "memory": "2048Mi"},
            "requests": {"cpu": "200m", "memory": "1024Mi"},
            "is_active": True,
            "is_builtin": True,
        },
        {
            "name": "1C1G",
            "limits": {"cpu": "1000m", "memory": "1024Mi"},
            "requests": {"cpu": "200m", "memory": "256Mi"},
            "is_active": True,
            "is_builtin": True,
        },
    ]

    for plan_data in need_add_plans:
        # 如果项目已经有该方案, 不做任何处理
        ResQuotaPlan.objects.using(schema_editor.connection.alias).get_or_create(
            name=plan_data["name"],
            defaults=plan_data,
        )



class Migration(migrations.Migration):

    dependencies = [
        ('bkapp_model', '0027_moduleprocessspec_graceful_shutdown_seconds'),
    ]

    operations = [
        migrations.RunPython(add_some_res_quota_plans, reverse_code=migrations.RunPython.noop),
    ]
