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
from typing import Optional

from django.core.management.base import BaseCommand
from paas_service.models import ServiceInstance


class Command(BaseCommand):
    help = '批量修改已分配 mysql 实例配置信息'

    def add_arguments(self, parser):
        parser.add_argument("--host", dest="host", help="实例 host，不填则不更新", default=None, required=False)
        parser.add_argument("--port", dest="port", help="实例 port，不填则不更新", default=None, required=False)
        parser.add_argument("--password", dest="password", help="实例 paasword，不填则不更新", default=None, required=False)

        parser.add_argument(
            "--no-dry-run", dest="dry_run", default=True, action="store_false", help="是否只打印实例 credentials 信息"
        )

    def handle(self, host: Optional[str], port: Optional[str], password: Optional[str], dry_run: bool, **options):
        svc_objs = ServiceInstance.objects.all()
        for obj in svc_objs:
            credentials = obj.get_credentials()

            has_changed = False
            if host:
                credentials["host"] = host
                has_changed = True

            if port:
                credentials["port"] = port
                has_changed = True

            if password:
                credentials["password"] = password
                has_changed = True

            if not dry_run:
                obj.credentials = json.dumps(credentials)
                if has_changed:
                    obj.save(update_fields=["credentials"])

            self.stdout.write(self.style.NOTICE(f'实例配置变化：\n before:{obj.get_credentials()} \n after:{credentials} \n'))
