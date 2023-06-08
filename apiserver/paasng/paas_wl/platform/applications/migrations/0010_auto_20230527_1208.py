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
# Generated by Django 3.2.12 on 2023-05-27 04:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0009_config_mount_app_log_to_host'),
    ]

    operations = [
        migrations.AddField(
            model_name='build',
            name='image',
            field=models.TextField(default='', help_text='运行 Build 的镜像地址, 对于构件类型为 image 的 Build 该值同时也是构建产物', null=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='build',
            name='artifact_deleted',
            field=models.BooleanField(default=False, help_text='slug/镜像是否已被清理'),
        ),
        migrations.AlterField(
            model_name='build',
            name='slug_path',
            field=models.TextField(help_text='slug path 形如 {region}/home/{name}:{branch}:{revision}/push', null=True),
        ),
        migrations.AlterField(
            model_name='buildprocess',
            name='image',
            field=models.CharField(help_text='builder image', max_length=512, null=True),
        ),
    ]
