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
import logging

from django.core.management.base import BaseCommand

from paasng.pluginscenter.itsm_adaptor.client import ItsmClient
from paasng.pluginscenter.itsm_adaptor.constants import ApprovalServiceName
from paasng.pluginscenter.itsm_adaptor.exceptions import (
    ItsmApiError,
    ItsmCatalogNotExistsError,
    ItsmGatewayServiceError,
)
from paasng.pluginscenter.models.instances import ApprovalService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "初始化流程服务到 ITSM，并将服务ID写入DB中方便后续提单使用"

    def handle(self, *args, **options):
        client = ItsmClient()

        try:
            plugin_center_catalog_id = client.get_plugin_center_catalog_id()
        except ItsmCatalogNotExistsError:
            # 插件开发者中心的服务目录不存在则需要在根目录下手动创建
            root_catalog_id = client.get_root_catalog_id()
            plugin_center_catalog_id = client.create_plugin_center_catalog(root_catalog_id)

        for service_name in ApprovalServiceName.get_values():
            # DB 中未存储服务ID信息，则需要手动创建
            svc_objects = ApprovalService.objects.filter(service_name=service_name)

            if svc_objects.exists() and svc_objects.first().service_id:
                logger.info("service({service_name}) information is already stored in DB")
                continue

            try:
                service_id = client.import_service(plugin_center_catalog_id, service_name)
            except (ItsmApiError, ItsmGatewayServiceError) as e:
                logger.error(e.message)
            else:
                ApprovalService.objects.update_or_create(
                    service_name=service_name,
                    defaults={
                        "service_id": service_id,
                    },
                )
                logger.info(f"import service({service_name}) to itsm success, service_id: {service_id}")
