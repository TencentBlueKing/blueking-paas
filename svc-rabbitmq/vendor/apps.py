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

from django.apps import AppConfig
from rest_framework.exceptions import ValidationError


def validate_plan_stream_port(sender, instance, **kwargs):
    """方案保存前校验 stream 端口，避免非法值被下发成应用的 RABBITMQ_STREAM_PORT

    抛 DRF 的异常是为了让平台管理端拿到 400 和具体原因，而不是没有说明的 500。
    """
    try:
        port = instance.get_config().get("stream_port")
    except (ValueError, AttributeError):
        # 配置不是合法 JSON 或不是对象，交由既有逻辑处理
        return

    if port is None or (isinstance(port, int) and 1 <= port <= 65535):
        return

    raise ValidationError({"stream_port": "端口需为 1–65535 的整数"})


class VendorConfig(AppConfig):
    name = "vendor"

    def ready(self):
        from django.db.models.signals import pre_save
        from paas_service.models import Plan

        pre_save.connect(validate_plan_stream_port, sender=Plan, dispatch_uid="vendor.validate_plan_stream_port")
