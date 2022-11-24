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
"""
A command for importing PreCreatedInstance.
"""
import argparse

import yaml
from django.core.management.base import BaseCommand

from paasng.dev_resources.services.models import Service
from paasng.dev_resources.services.serializers import PreCreatedInstanceImportSLZ


def _get_service_choices():
    choices = []
    for svc in Service.objects.all():
        if svc.provider_name == "pool":
            choices.append(f"{svc.region}:{svc.name}")
    return choices


class Command(BaseCommand):
    """导入资源池实例"""

    def add_arguments(self, parser):
        parser.add_argument(
            "--service",
            dest="service_name",
            required=True,
            help="Add-ons service name",
            choices=_get_service_choices(),
        )
        parser.add_argument(
            "-f",
            "--file",
            dest="file_",
            required=True,
            type=argparse.FileType(),
            help="yaml file path describing the instance configuration",
        )

    def handle(self, service_name: str, file_, **options):
        region, name = service_name.split(":")
        svc = Service.objects.get_by_natural_key(region, name)

        with file_ as fh:
            data = list(yaml.safe_load_all(fh))

        slz = PreCreatedInstanceImportSLZ(data=data, context={"service": svc}, many=True)
        slz.is_valid(raise_exception=True)
        slz.save()
