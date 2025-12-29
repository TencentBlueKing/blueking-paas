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

from django.db import migrations, models
import jsonfield.fields

def init_res_quota_plans(apps, schema_editor):
    """Initialize resource quota plans"""
    ResQuotaPlan = apps.get_model("bkapp_model", "ResQuotaPlan")

    initial_plans = [
        {
            "plan_name": "default",
            "limits": {"cpu": "4000m", "memory": "1024Mi"},
            "requests": {"cpu": "200m", "memory": "256Mi"},
            "is_active": True,
            "is_builtin": True,
        },
        {
            "plan_name": "4C1G",
            "limits": {"cpu": "4000m", "memory": "1024Mi"},
            "requests": {"cpu": "200m", "memory": "256Mi"},
            "is_active": True,
            "is_builtin": True,
        },
        {
            "plan_name": "4C2G",
            "limits": {"cpu": "4000m", "memory": "2048Mi"},
            "requests": {"cpu": "200m", "memory": "1024Mi"},
            "is_active": True,
            "is_builtin": True,
        },
        {
            "plan_name": "4C4G",
            "limits": {"cpu": "4000m", "memory": "4096Mi"},
            "requests": {"cpu": "200m", "memory": "2048Mi"},
            "is_active": True,
            "is_builtin": True,
        },
    ]

    for plan_data in initial_plans:
        ResQuotaPlan.objects.using(schema_editor.connection.alias).get_or_create(
            plan_name=plan_data["plan_name"],
            defaults=plan_data,
        )

class Migration(migrations.Migration):

    dependencies = [
        ('bkapp_model', '0021_processspecenvoverlay_override_proc_res'),
    ]

    operations = [
        migrations.CreateModel(
            name='ResQuotaPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('region', models.CharField(help_text='部署区域', max_length=32)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('plan_name', models.CharField(max_length=64, unique=True, verbose_name='方案名称')),
                ('limits', jsonfield.fields.JSONField(default={})),
                ('requests', jsonfield.fields.JSONField(default={})),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
                ('is_builtin', models.BooleanField(default=False, verbose_name='是否为内置方案')),
            ],
            options={
                'ordering': ['created'],
            },
        ),

        migrations.RunPython(init_res_quota_plans),
    ]
