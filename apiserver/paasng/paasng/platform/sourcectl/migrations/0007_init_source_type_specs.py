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

import logging

from django.db import migrations

logger = logging.getLogger(__name__)


def init_source_type_specs(apps, schema_editor):
    """初始化代码库配置（BareGit, BaseSVN）"""
    SourceTypeSpecConfig = apps.get_model('sourcectl', 'SourceTypeSpecConfig')

    logger.info("初始化 BareGit 代码库配置")
    SourceTypeSpecConfig.objects.create(
        name='bare_git', label_en='BareGit', label_zh_cn='原生 Git', enabled=True,
        spec_cls='paasng.platform.sourcectl.type_specs.BareGitSourceTypeSpec'
    )

    logger.info("初始化 BareSVN 代码库配置")
    SourceTypeSpecConfig.objects.create(
        name='bare_svn', label_en='BareSVN', label_zh_cn='原生 SVN', enabled=True,
        spec_cls='paasng.platform.sourcectl.type_specs.BareSvnSourceTypeSpec'
    )
    logger.info("初始化代码库配置完成")


class Migration(migrations.Migration):
    dependencies = [
        ('sourcectl', '0006_sourcetypespecconfig'),
    ]

    operations = [
        migrations.RunPython(init_source_type_specs),
    ]
