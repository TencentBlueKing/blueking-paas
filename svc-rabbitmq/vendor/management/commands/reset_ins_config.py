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
from django.core.management.base import BaseCommand
from vendor.models import Cluster


class Command(BaseCommand):
    help = '批量修改已分配 rabbitmq 实例配置信息'

    def add_arguments(self, parser):
        parser.add_argument("--host", dest="host", help="host", default="", required=False)
        parser.add_argument("--port", dest="port", help="port", default="", required=False)
        parser.add_argument("--password", dest="password", help="paasword", default="", required=False)
        parser.add_argument("--management_api", dest="management_api", help="管理地址", default="", required=False)

        parser.add_argument(
            "--no-dry-run", dest="dry_run", default=True, action="store_false", help="是否只打印实例 credentials 信息"
        )

    def handle(self, host, port, password, management_api, dry_run, **options):
        cluster_objs = Cluster.objects.all()
        for cluster in cluster_objs:
            if not dry_run:
                cluster.host = host or cluster.host
                cluster.port = port or cluster.port
                cluster.password = password or cluster.password
                cluster.management_api = management_api or cluster.management_api
                cluster.save(update_fields=["host", "port", "password", "management_api"])
            else:
                self.stdout.write(
                    self.style.NOTICE(
                        f'实例配置变化：'
                        f'\n before:(host:{cluster.host} port:{cluster.port} password:{cluster.password}'
                        f' management_api:{cluster.management_api}) \n '
                        f'after:( host:{host} port:{port} password:{password} management_api:{management_api}) \n'
                    )
                )
