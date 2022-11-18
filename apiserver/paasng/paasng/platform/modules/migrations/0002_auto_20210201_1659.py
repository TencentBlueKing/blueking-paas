# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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
# Generated by Django 2.2.17 on 2021-02-01 08:59

from django.db import migrations
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='appslugbuilder',
            name='labels',
            field=jsonfield.fields.JSONField(blank=True, default=dict, verbose_name='镜像标签'),
        ),
        migrations.AddField(
            model_name='appslugrunner',
            name='labels',
            field=jsonfield.fields.JSONField(blank=True, default=dict, verbose_name='镜像标签'),
        ),
    ]
