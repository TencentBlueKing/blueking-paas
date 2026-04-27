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

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from paasng.accessories.log.models import TenantLogConfig
from paasng.core.tenant.user import get_init_tenant_id


class Command(BaseCommand):
    help = "Create TenantLogConfig for a tenant"
    config_fields = (
        "storage_cluster_id",
        "retention",
        "es_shards",
        "storage_replicas",
        "time_zone",
        "shared_bk_biz_id",
    )

    def add_arguments(self, parser):
        tenant_group = parser.add_mutually_exclusive_group(required=True)
        tenant_group.add_argument("--tenant-id", help="tenant id")
        tenant_group.add_argument(
            "--default-tenant",
            action="store_true",
            default=False,
            help="为默认租户创建配置，不可与 --tenant-id 同时指定",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            default=False,
            help="允许更新相同 tenant_id 已存在的配置",
        )
        parser.add_argument("--storage-cluster-id", required=True, type=int, help="日志平台存储集群 ID")
        parser.add_argument("--retention", type=int, default=14, help="日志保存时间（天），默认 14")
        parser.add_argument("--es-shards", type=int, default=1, help="ES 索引分片数，默认 1")
        parser.add_argument("--storage-replicas", type=int, default=1, help="存储副本数，默认 1")
        parser.add_argument("--time-zone", type=int, default=8, help="时区，如 8 表示 UTC+8，默认 8")
        parser.add_argument(
            "--shared-bk-biz-id",
            type=int,
            default=None,
            help="平台级共享采集项所属的 CMDB 业务 ID (非 space_id)，仅在启用 ENABLE_SHARED_BK_LOG_INDEX 时需要",
        )

    def handle(self, *args, **options):
        tenant_id = get_init_tenant_id() if options["default_tenant"] else options["tenant_id"]
        config_data = {field: options[field] for field in self.config_fields}
        allow_update = options["update"]
        existing = TenantLogConfig.objects.filter(tenant_id=tenant_id).first()

        if existing and not allow_update:
            raise CommandError(f"TenantLogConfig already exists for tenant_id={tenant_id}, use --update to overwrite")

        try:
            config = existing or TenantLogConfig(tenant_id=tenant_id)
            for field, value in config_data.items():
                setattr(config, field, value)
            action = "Updated" if existing else "Created"

            config.full_clean()
            if existing:
                config.save(update_fields=[*config_data.keys(), "updated"])
            else:
                config.save()
        except ValidationError as e:
            raise CommandError(f"Invalid TenantLogConfig data: {e}")

        self.stdout.write(
            self.style.SUCCESS(
                f"{action} TenantLogConfig for tenant_id={tenant_id}: "
                f"storage_cluster_id={config.storage_cluster_id}, retention={config.retention}, "
                f"es_shards={config.es_shards}, storage_replicas={config.storage_replicas}, "
                f"time_zone={config.time_zone}, shared_bk_biz_id={config.shared_bk_biz_id}"
            )
        )
