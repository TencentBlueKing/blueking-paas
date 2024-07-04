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

# Generated by Django 2.2.17 on 2022-01-24 02:47

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('api', '0007_config_runtime'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppImageCredential',
            fields=[
                ('uuid', models.UUIDField(auto_created=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True, verbose_name='UUID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('registry', models.CharField(max_length=255)),
                ('username', models.CharField(max_length=32)),
                ('password', models.CharField(max_length=255)),
                ('app', models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, to='api.App')),
            ],
            options={
                'unique_together': {('app', 'registry')},
            },
        ),
    ]
