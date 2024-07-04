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

# Generated by Django 3.2.12 on 2024-01-29 08:09

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AppResourceUsageReport',
            fields=[
                ('app_code', models.CharField(max_length=128, primary_key=True, serialize=False, verbose_name='应用 Code')),
                ('app_name', models.CharField(max_length=128, verbose_name='应用名称')),
                ('cpu_requests', models.IntegerField(default=0, verbose_name='CPU 请求')),
                ('mem_requests', models.IntegerField(default=0, verbose_name='内存请求')),
                ('cpu_limits', models.IntegerField(default=0, verbose_name='CPU 限制')),
                ('mem_limits', models.IntegerField(default=0, verbose_name='内存限制')),
                ('cpu_usage_avg', models.FloatField(default=0, verbose_name='CPU 平均使用率')),
                ('mem_usage_avg', models.FloatField(default=0, verbose_name='内存平均使用率')),
                ('pv', models.BigIntegerField(default=0, verbose_name='近一周页面访问量')),
                ('uv', models.BigIntegerField(default=0, verbose_name='近一周访问用户数')),
                ('summary', models.JSONField(default=dict, verbose_name='资源使用详情汇总')),
                ('operator', models.CharField(max_length=128, null=True, verbose_name='最后操作人')),
                ('collected_at', models.DateTimeField(verbose_name='数据统计时间')),
            ],
        ),
    ]
