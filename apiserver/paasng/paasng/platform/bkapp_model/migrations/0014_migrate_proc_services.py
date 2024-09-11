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

from django.conf import settings
from django.db import migrations

from paasng.platform.bkapp_model.entities import ProcService


def init_proc_services_by_web_proc(apps, schema_editor):
    """为存量配置初始化 services"""
    ModuleProcessSpec = apps.get_model("bkapp_model", "ModuleProcessSpec")

    for spec in ModuleProcessSpec.objects.all():
        svc = {"name": "http", "protocol": "TCP", "port": 80, "target_port": spec.port or settings.CONTAINER_PORT}
        if spec.name == "web":
            svc["exposed_type"] = {"name": "bk/http"}

        spec.services = [ProcService(**svc)]
        spec.save(update_fields=["services"])


def reverse_proc_services(apps, schema_editor):
    """回滚清空 services 字段"""
    ModuleProcessSpec = apps.get_model("bkapp_model", "ModuleProcessSpec")
    ModuleProcessSpec.objects.all().update(services=None)


class Migration(migrations.Migration):

    dependencies = [
        ('bkapp_model', '0013_moduleprocessspec_services'),
    ]

    operations = [
        migrations.RunPython(init_proc_services_by_web_proc, reverse_proc_services),
    ]
