# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
"""
A command for Query  relationship between PreCreatedInstance and Application(Module, Env)
"""
import json
from typing import Dict, Optional

from django.core.management.base import BaseCommand

from paasng.dev_resources.services.models import PreCreatedInstance, Service, ServiceInstance
from paasng.platform.environments.models import ModuleEnvironment


def _get_service_choices():
    choices = []
    for svc in Service.objects.all():
        if svc.provider_name == "pool":
            choices.append(f"{svc.region}:{svc.name}")
    return choices


def get_related_env(item: PreCreatedInstance) -> Optional[ModuleEnvironment]:
    if not item.is_allocated:
        return None
    qs = ServiceInstance.objects.filter(plan=item.plan)
    for instance in qs.all():
        if instance.config.get("__pk__") == str(item.pk) and instance.service_attachment.count() == 1:
            attachment = instance.service_attachment.get()
            break
    else:
        return None
    return attachment.engine_app.env


def fuzzy_compare(credentials_left: Dict, credentials_right: Dict) -> bool:
    """Return True if all items in credentials_left is equal the counterpart in credentials_right, otherwise, False"""
    for key, value in credentials_left.items():
        if key not in credentials_right or credentials_right[key] != value:
            return False
    return True


class Command(BaseCommand):
    """查询资源池实例的绑定关系"""

    def add_arguments(self, parser):
        parser.add_argument(
            "--service",
            dest="service_name",
            required=True,
            help="Add-ons service name",
            choices=_get_service_choices(),
        )
        parser.add_argument(
            "--credentials",
            dest="credentials_str",
            required=True,
            help="增强服务实例的实例配置(json format), 支持只传部分属性做模糊匹配, "
            "例如 '{\"host\": \"xxx.xxx.xxx.xxx\"}' 将匹配所有 host 为 xxx.xxx.xxx.xxx 的实例",
        )

    def handle(self, service_name: str, credentials_str: str, **options):
        credentials = json.loads(credentials_str)
        region, name = service_name.split(":")
        svc = Service.objects.get_by_natural_key(region, name)
        qs = PreCreatedInstance.objects.filter(plan__in=svc.plan_set.all())
        self.stdout.write("\n")
        for item in qs.all():
            if not fuzzy_compare(credentials, json.loads(item.credentials)):
                continue
            env = get_related_env(item)
            if not env:
                continue
            self.stdout.write(
                f"应用名称: {env.application.name}\t应用ID: {env.application.code}\t"
                f"模块名称: {env.module.name}\t环境: {env.environment}"
            )
