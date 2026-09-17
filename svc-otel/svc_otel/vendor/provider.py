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

import logging
from dataclasses import dataclass
from typing import Dict

from django.conf import settings
from paas_service.base_vendor import BaseProvider, InstanceData

from svc_otel.bkmonitorv3.client import make_bk_monitor_client
from svc_otel.vendor.models import ApmData

logger = logging.getLogger(__name__)


@dataclass
class Provider(BaseProvider):
    SERVICE_NAME = "otel"

    def _apply_data_token(self, bk_app_code: str, env: str, bk_monitor_space_id: str, tenant_id: str) -> ApmData:
        """到蓝鲸监控 OTEL 服务给应用申请 data_token"""
        apm_data = ApmData.objects.filter(bk_app_code=bk_app_code, env=env).first()
        if apm_data:
            return apm_data

        # 使用稳定名称复用监控实例，并将 APM 名称不允许的连字符转换为 0us0。
        app_name = f"bkapp_{bk_app_code}_{env}".replace("-", "0us0")
        client = make_bk_monitor_client(tenant_id)
        data_token = client.get_or_create_apm(app_name, bk_monitor_space_id)

        # 并发申请时优先沿用已写入的本地记录，避免覆盖有效 token
        apm_data, _created = ApmData.objects.get_or_create(
            bk_app_code=bk_app_code, env=env, defaults={"data_token": data_token, "app_name": app_name}
        )
        return apm_data

    def create(self, params: Dict) -> InstanceData:
        logger.info("正在创建增强服务实例...")

        bk_app_code = params.get("app_code")
        env = params.get("env")
        bk_monitor_space_id = params.get("bk_monitor_space_id")
        tenant_id = params.get("tenant_id")
        apm_data = self._apply_data_token(bk_app_code, env, bk_monitor_space_id, tenant_id)

        return InstanceData(
            credentials={
                "trace": True,
                "sampler": "parentbased_always_on",
                "bk_data_token": apm_data.data_token,
                "grpc_url": settings.BK_OTEL_GRPC_URL,
            },
            config={
                "bk_monitor_space_id": bk_monitor_space_id,
                "bk_app_code": bk_app_code,
                "app_name": apm_data.app_name,
                "env": env,
            },
        )

    def delete(self, instance_data: InstanceData):
        """蓝鲸监控 OTEL 服务未提供删除 datatoken 的 API"""
        logger.info("正在删除增强服务实例...")

    def patch(self, instance_data: InstanceData, params: Dict) -> InstanceData:
        raise NotImplementedError
