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

from django.core.management.base import BaseCommand
from paas_service.models import ServiceInstance


class Command(BaseCommand):
    help = '批量修改已分配 mysql 实例配置信息'

    def add_arguments(self, parser):
        parser.add_argument("--host", dest="host", help="实例 host", default="", required=False)
        parser.add_argument("--port", dest="port", help="实例 port", default="", required=False)
        parser.add_argument("--password", dest="password", help="实例 paasword", default="", required=False)

        parser.add_argument(
            "--no-dry-run", dest="dry_run", default=True, action="store_false", help="是否只打印实例 credentials 信息"
        )

    def handle(self, host, port, password, dry_run, **options):
        svc_objs = ServiceInstance.objects.all()
        for obj in svc_objs:
            credentials = obj.get_credentials()
            credentials["host"] = host or credentials["host"]
            credentials["port"] = port or credentials["port"]
            credentials["password"] = password or credentials["password"]

            if not dry_run:
                obj.credentials = json.dumps(credentials)
                obj.save(update_fields=["credentials"])
            else:
                self.stdout.write(
                    self.style.NOTICE(f'实例配置变化：\n before:{obj.get_credentials()} \n after:{credentials} \n')
                )
