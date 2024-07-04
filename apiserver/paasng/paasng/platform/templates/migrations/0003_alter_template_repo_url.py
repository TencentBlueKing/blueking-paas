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

# Generated by Django 3.2.12 on 2022-09-15 01:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('templates', '0002_template_processes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='template',
            name='repo_url',
            field=models.CharField(blank=True, default='', max_length=256, verbose_name='代码仓库信息'),
        ),
    ]
