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
# Generated by Django 3.2.12 on 2023-06-08 07:40

from django.db import migrations, models
import paas_wl.platform.applications.constants


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0010_auto_20230527_1208'),
    ]

    operations = [
        migrations.AddField(
            model_name='build',
            name='image_id',
            field=models.CharField(help_text='镜像摘要(例如, sha256:xxx)', max_length=128, null=True),
        ),
        migrations.AddField(
            model_name='build',
            name='artifact_type',
            field=models.CharField(default=paas_wl.platform.applications.constants.ArtifactType['SLUG'],
                                   help_text='构建产物类型', max_length=16),
        ),
    ]
