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

from django.conf import settings
from django.core.management.base import BaseCommand
from vendor.client import Client
from vendor.models import Cluster


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--name", required=True)
        parser.add_argument("--host", required=True)
        parser.add_argument("--port", default=5672, type=int)
        parser.add_argument("--api-port", default=15672, type=int)
        parser.add_argument("--api-url", default=None)
        parser.add_argument("--admin", default="admin")
        parser.add_argument("--password", required=True)
        parser.add_argument("--cluster-version", default="3.7.8")
        parser.add_argument("--disable", default=False, action="store_true")
        parser.add_argument("--extra", default={}, type=json.loads)
        parser.add_argument("--check", default=False, action="store_true")

    def handle(
        self,
        name,
        host,
        port,
        api_url,
        api_port,
        admin,
        password,
        cluster_version,
        disable,
        extra,
        check,
        *args,
        **kwargs
    ):
        if not api_url:
            api_url = "http://%s:%s" % (host, api_port)

        cluster, created = Cluster.objects.update_or_create(
            name=name,
            defaults={
                "host": host,
                "port": port,
                "management_api": api_url,
                "admin": admin,
                "password": password,
                "version": cluster_version,
                "enable": not disable,
                "extra": extra,
            },
        )

        alive = "unknown"
        if check:
            client = Client.from_cluster(cluster)
            client.user.set_permission(
                username=admin,
                virtual_host="/",
                configure_regex=settings.RABBITMQ_DEFAULT_USER_CONFIGURE_PERMISSIONS,
                write_regex=settings.RABBITMQ_DEFAULT_USER_WRITE_PERMISSIONS,
                read_regex=settings.RABBITMQ_DEFAULT_USER_READ_PERMISSIONS,
            )
            alive = "ok" if client.alive(virtual_host="/") else "fail"

        print("cluster %s created, pk %s, created %s, alive %s" % (cluster.name, cluster.pk, created, alive))
