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

# Generated by Django 3.2.12 on 2023-04-13 09:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0009_application_is_scene_app'),
        ('log', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='processlogqueryconfig',
            name='process_type',
            field=models.CharField(blank=True, max_length=16, null=True, verbose_name='进程类型(名称)'),
        ),
        migrations.AlterUniqueTogether(
            name='processlogqueryconfig',
            unique_together={('env', 'process_type')},
        ),
    ]
