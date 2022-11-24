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
import json
import logging

from django.core.management.base import BaseCommand, CommandParser

from paasng.dev_resources.servicehub import models

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Add LEGACY_ prefix to legacy rabbitmq instance credentials"

    def add_arguments(self, parser: CommandParser):
        parser.add_argument("-n", "--name", default="rabbitmq", help="rabbitmq service name")
        parser.add_argument("-r", "--region", help="rabbitmq service region")
        parser.add_argument("--id", help="rabbitmq service id")
        parser.add_argument("--dry-run", default=False, action="store_true", help="dry run")

    def handle(self, name, region, id, dry_run, *args, **options):
        services = models.Service.objects.all()
        if name:
            services = services.filter(name=name)

        if region:
            services = services.filter(region=region)

        if id:
            services = services.filter(pk=id)

        service = services.get()

        for i in models.ServiceInstance.objects.filter(service=service):
            if not i.credentials:
                print(f"credentials of instance {i.pk} is None")
                continue

            credentials = json.loads(i.credentials)

            if not credentials:
                print(f"credentials of instance {i.pk} is empty")
                continue

            to_update = {}
            prefix = "LEGACY_"

            for k, v in credentials.items():
                if not k.startswith(prefix):
                    to_update[f"{prefix}{k}"] = v

            if not to_update:
                continue

            print(f"updating instance {i.pk}")
            credentials.update(to_update)

            if not dry_run:
                i.credentials = json.dumps(credentials)
                i.save(update_fields=["credentials"])
