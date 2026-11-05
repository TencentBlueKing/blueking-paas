# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from vendor.client import Client
from vendor.models import Cluster, ClusterTag
from vendor.provider import Provider


class Command(BaseCommand):
    help = "Register or update a rabbitmq cluster with tags, used by plan.config.cluster_selector"

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True, help="集群名称，已存在时更新")
        parser.add_argument("--host", required=True)
        parser.add_argument("--port", default=5672, type=int)
        parser.add_argument("--api-port", default=15672, type=int)
        parser.add_argument("--api-url", default=None, help="管理 API 地址，默认为 http://{host}:{api-port}")
        parser.add_argument("--admin", default="admin")
        parser.add_argument("--password", required=True)
        parser.add_argument("--cluster-version", required=True)
        parser.add_argument("--disable", default=False, action="store_true", help="注册为停用状态")
        parser.add_argument(
            "--tag",
            dest="tags",
            default=[],
            action="append",
            help="集群标签，格式为 key=value，可重复传入；未传入的存量标签会被删除",
        )
        parser.add_argument("--extra", default={}, type=json.loads, help='额外信息，如 {"tls": {"ca": "..."}}')
        parser.add_argument("--check", default=False, action="store_true", help="注册后授权管理员并探活")
        parser.add_argument("--dry-run", default=False, action="store_true")

    def handle(self, name, host, port, api_url, api_port, admin, password, cluster_version, **options):
        tags = self.parse_tags(options["tags"])
        defaults = {
            "host": host,
            "port": port,
            "management_api": api_url or f"http://{host}:{api_port}",
            "admin": admin,
            "password": password,
            "version": cluster_version,
            "enable": not options["disable"],
            "extra": options["extra"],
        }

        if options["dry_run"]:
            insensitive = {k: v for k, v in defaults.items() if k not in ("password", "extra")}
            self.stdout.write(f"[DRY-RUN] register cluster {name}: {insensitive}, tags {tags}")
            return

        with transaction.atomic():
            cluster, created = Cluster.objects.update_or_create(name=name, defaults=defaults)
            cluster.tags.exclude(key__in=tags.keys()).delete()
            for key, value in tags.items():
                ClusterTag.objects.update_or_create(instance=cluster, key=key, defaults={"value": value})

        alive = "unknown"
        if options["check"]:
            client = Client.from_cluster(Provider.to_runtime_cluster(cluster))
            client.user.set_permission(
                username=admin,
                virtual_host="/",
                configure_regex=settings.RABBITMQ_DEFAULT_USER_CONFIGURE_PERMISSIONS,
                write_regex=settings.RABBITMQ_DEFAULT_USER_WRITE_PERMISSIONS,
                read_regex=settings.RABBITMQ_DEFAULT_USER_READ_PERMISSIONS,
            )
            alive = "ok" if client.alive() else "fail"

        self.stdout.write(
            f"cluster {cluster.name} registered, pk {cluster.pk}, created {created}, alive {alive}, tags {tags}"
        )

    @staticmethod
    def parse_tags(tags):
        parsed = {}
        for tag in tags:
            key, sep, value = tag.partition("=")
            key, value = key.strip(), value.strip()
            if not sep or not key or not value:
                raise CommandError(f"invalid --tag value {tag!r}, expected key=value")
            parsed[key] = value
        return parsed
