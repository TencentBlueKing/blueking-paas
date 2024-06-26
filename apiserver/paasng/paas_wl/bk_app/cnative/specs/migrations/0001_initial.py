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

# Generated by Django 3.2.12 on 2022-07-05 03:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AppModelRevision',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('region', models.CharField(help_text='部署区域', max_length=32)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('application_id', models.UUIDField(verbose_name='所属应用')),
                ('module_id', models.UUIDField(verbose_name='所属模块')),
                ('version', models.CharField(max_length=64, verbose_name='模型版本')),
                ('yaml_value', models.TextField(verbose_name='应用模型（YAML 格式）')),
                ('json_value', models.JSONField(verbose_name='应用模型（JSON 格式）')),
                ('has_deployed', models.BooleanField(default=False, verbose_name='是否已部署')),
                ('is_draft', models.BooleanField(default=False, verbose_name='是否草稿')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='是否已删除')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AppModelResource',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('region', models.CharField(help_text='部署区域', max_length=32)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('application_id', models.UUIDField(verbose_name='所属应用')),
                ('module_id', models.UUIDField(unique=True, verbose_name='所属模块')),
                ('revision', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='specs.appmodelrevision', verbose_name='当前 revision')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
