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
    help = "批量修改已分配 rabbitmq 实例配置信息"

    def add_arguments(self, parser):
        parser.add_argument("--host", dest="host", help="host，不填则不更新", default=None)
        parser.add_argument("--port", dest="port", help="port，不填则不更新", default=None)
        parser.add_argument("--password", dest="password", help="paasword，不填则不更新", default=None)
        parser.add_argument(
            "--api-port", dest="api-port", help="api-port，与 host 组成 api-url ", default=None, type=int
        )
        parser.add_argument("--api-url", dest="api-url", help="api-url，不填则由 host 与 api-port 组成", default=None)
        parser.add_argument("--admin", dest="admin", help="admin，不填则不更新", default=None)

        parser.add_argument(
            "--no-dry-run", dest="dry_run", default=True, action="store_false", help="是否只打印实例 credentials 信息"
        )

    def handle(
        self,
        host: Optional[str],
        port: Optional[str],
        password: Optional[str],
        api_port: Optional[int],
        api_url: Optional[str],
        admin: Optional[str],
        dry_run: bool,
        **options,
    ):
        svc_objs = ServiceInstance.objects.all()
        for svc_obj in svc_objs:
            credentials = svc_obj.get_credentials()
            updated_credentials = credentials.copy()

            if api_url:
                updated_credentials["management_api"] = api_url
            elif host and api_port:
                updated_credentials["management_api"] = "http://%s:%s" % (host, api_port)

            if host:
                updated_credentials["host"] = host

            if port:
                updated_credentials["port"] = port

            if password:
                updated_credentials["password"] = password

            if admin:
                updated_credentials["admin"] = admin

            if not dry_run and updated_credentials != credentials:
                svc_obj.credentials = json.dumps(updated_credentials)
                svc_obj.save(update_fields=["credentials"])

            self.stdout.write(
                self.style.NOTICE(f"实例配置变化：\n before:{credentials} \n after:{updated_credentials} \n")
            )
