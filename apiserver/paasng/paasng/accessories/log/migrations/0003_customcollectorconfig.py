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

# Generated by Django 3.2.12 on 2023-05-04 02:32

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0006_auto_20220509_1544'),
        ('log', '0002_auto_20230413_1744'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomCollectorConfig',
            fields=[
                ('uuid', models.UUIDField(auto_created=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True, verbose_name='UUID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('name_en', models.CharField(help_text='5-50个字符，仅包含字母数字下划线, 查询索引是 name_en-*', max_length=50, unique=True, verbose_name='自定义采集项名称')),
                ('collector_config_id', models.BigIntegerField(help_text='采集配置ID', unique=True, verbose_name='采集配置ID')),
                ('index_set_id', models.BigIntegerField(help_text='查询时使用', verbose_name='索引集ID', null=True)),
                ('bk_data_id', models.BigIntegerField(verbose_name='数据管道ID')),
                ('log_paths', models.JSONField(verbose_name='日志采集路径')),
                ('log_type', models.CharField(max_length=32, verbose_name='日志类型')),
                ('module', models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, to='modules.module')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
