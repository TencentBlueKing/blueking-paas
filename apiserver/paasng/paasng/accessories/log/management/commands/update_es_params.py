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
from django.core.management.base import BaseCommand

from paasng.accessories.log.models import ElasticSearchConfig
from paasng.accessories.log.shim.setup_elk import (
    ELK_INGRESS_COLLECTOR_CONFIG_ID,
    ELK_STDOUT_COLLECTOR_CONFIG_ID,
    ELK_STRUCTURED_COLLECTOR_CONFIG_ID,
    construct_platform_es_params,
)


class Command(BaseCommand):
    help = '"Update ElasticSearch query parameters, executed when modifying ES query configuration."'

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant_id",
            type=str,
            help="Specify the tenant ID to update. If not provided, updates all tenants.",
        )

    def handle(self, *args, **options):
        tenant_id = options.get("tenant_id")
        # 获取最新的 Elasticsearch 查询参数
        search_params = construct_platform_es_params()

        collector_configs = [
            (ELK_STDOUT_COLLECTOR_CONFIG_ID, search_params.stdout),
            (ELK_STRUCTURED_COLLECTOR_CONFIG_ID, search_params.structured),
            (ELK_INGRESS_COLLECTOR_CONFIG_ID, search_params.ingress),
        ]

        if tenant_id:
            for config_id, params in collector_configs:
                ElasticSearchConfig.objects.filter(
                    tenant_id=tenant_id,
                    collector_config_id=config_id,
                    backend_type="es",
                ).update(search_params=params)
                self.stdout.write(self.style.SUCCESS(f"Updating {config_id} search_params for tenant: {tenant_id}"))
        else:
            for config_id, params in collector_configs:
                ElasticSearchConfig.objects.filter(
                    collector_config_id=config_id,
                    backend_type="es",
                ).update(search_params=params)
                self.stdout.write(self.style.SUCCESS(f"Updating {config_id} search_params for all tenants"))
