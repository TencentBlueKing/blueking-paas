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
from django.db import migrations
from django.conf import settings


def load_data(apps, schema_editor):
    """
    修改默认服务的中文名称
    """
    Service = apps.get_model("paas_service", "service")
    
    Service.objects.filter(display_name_zh_cn="蓝盾制品库", name="bkrepo").update(display_name_zh_cn="蓝鲸制品库")


class Migration(migrations.Migration):

    dependencies = [
        ('paas_service', '0008_auto_20220426_0429'),
    ]

    operations = [
        migrations.RunPython(load_data)
    ]