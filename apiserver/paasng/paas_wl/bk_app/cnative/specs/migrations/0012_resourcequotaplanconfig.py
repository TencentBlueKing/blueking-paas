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

from django.db import migrations, models

def init_res_quota_plans(apps, schema_editor):
    """Initialize resource quota plans"""
    ResQuotaPlan = apps.get_model("specs", "ResQuotaPlan")

    initial_plans = [
        {
            "plan_name": "default",
            "cpu_limit": "4000m",
            "memory_limit": "1024Mi",
            "cpu_request": "200m",
            "memory_request": "256Mi",
            "is_active": True,
            "is_builtin": True,
        },
        {
            "plan_name": "4C1G",
            "cpu_limit": "4000m",
            "memory_limit": "1024Mi",
            "cpu_request": "200m",
            "memory_request": "256Mi",
            "is_active": True,
            "is_builtin": True,
        },
        {
            "plan_name": "4C2G",
            "cpu_limit": "4000m",
            "memory_limit": "2048Mi",
            "cpu_request": "200m",
            "memory_request": "1024Mi",
            "is_active": True,
            "is_builtin": True,
        },
        {
            "plan_name": "4C4G",
            "cpu_limit": "4000m",
            "memory_limit": "4096Mi",
            "cpu_request": "200m",
            "memory_request": "2048Mi",
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
        ('specs', '0011_configmapsource_tenant_id_mount_tenant_id_and_more'),
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
                ('cpu_limit', models.CharField(max_length=8, verbose_name='CPU 限制 (millicores)')),
                ('memory_limit', models.CharField(max_length=8, verbose_name='内存限制 (MiB)')),
                ('cpu_request', models.CharField(max_length=8, verbose_name='CPU 请求 (millicores)')),
                ('memory_request', models.CharField(max_length=8, verbose_name='内存请求 (MiB)')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
                ('is_builtin', models.BooleanField(default=False, verbose_name='是否为内置方案')),
                ('tenant_id', models.CharField(db_index=True, default='default', help_text='本条数据的所属租户', max_length=32, verbose_name='租户 ID')),
            ],
            options={
                'abstract': False,
            },
        ),

        migrations.RunPython(init_res_quota_plans),
    ]
