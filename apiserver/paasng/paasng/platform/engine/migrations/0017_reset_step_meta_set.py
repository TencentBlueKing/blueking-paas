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

from django.db import migrations


def reset_step_meta_set(apps, schema_editor):
    """删除 docker-build 和 image-release 两个步骤, 以便在代码逻辑中重置它们"""
    StepMetaSet = apps.get_model('engine', 'StepMetaSet')
    StepMetaSet.objects.filter(name__in=['docker-build', 'image-release']).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('engine', '0016_deployment_bkapp_release_id'),
    ]

    operations = [
        migrations.RunPython(reset_step_meta_set),
    ]