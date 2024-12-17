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
import cattr
from django.core.management.base import BaseCommand

from paasng.accessories.log.models import ElasticSearchHost
from paasng.accessories.log.shim.setup_elk import setup_platform_elk_config


class Command(BaseCommand):
    help = "Initialize ElasticSearch configuration, executed when adding a new tenant."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant_id",
            type=str,
            required=True,
            help="Specify the tenant ID to update. If not provided, updates all tenants.",
        )
        parser.add_argument(
            "--host",
            type=str,
            required=True,
            help="The hostname or IP address of the Elasticsearch server.",
        )
        parser.add_argument(
            "--port",
            type=int,
            required=True,
            help="The port number of the Elasticsearch server.",
        )
        parser.add_argument(
            "--http_auth",
            type=str,
            help="Credentials in the format username:password for HTTP authentication.",
        )
        parser.add_argument(
            "--url_prefix",
            type=str,
            default="",
            help="URL prefix for Elasticsearch.",
        )
        parser.add_argument(
            "--use_ssl",
            action="store_true",
            help="Specify this flag to use SSL for the connection.",
        )

    def handle(self, tenant_id: str, *args, **options):
        es_host = cattr.structure(
            {
                "host": options["host"],
                "port": options["port"],
                "http_auth": options.get("http_auth"),
                "url_prefix": options["url_prefix"],
                "use_ssl": options.get("use_ssl", False),
            },
            ElasticSearchHost,
        )
        setup_platform_elk_config(tenant_id, es_host)
