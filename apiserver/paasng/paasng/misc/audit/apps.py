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
from django.apps import AppConfig
from django.conf import settings


class AuditConfig(AppConfig):
    name = "paasng.misc.audit"
    verbose_name = "audit"

    def ready(self):
        from . import handlers  # noqa: F401

        if not settings.BK_AUDIT_DATA_TOKEN or not settings.BK_AUDIT_ENDPOINT:
            return

        # TODO bk_audit SDK 默认的注册方法中要求必须定一个 APP_CODE\SECRET 这两个变量，
        # 并代表应用 ID 和 应用密钥，与开发者中心的定义冲突
        # 故先手动处理，SDK 短期内无法处理这个问题
        from bk_audit.contrib.bk_audit.settings import bk_audit_settings
        from bk_audit.contrib.opentelemetry.setup import setup

        from paasng.misc.audit.client import bk_audit_client

        setup(
            bk_audit_client,
            bk_data_id=bk_audit_settings.bk_data_id,
            bk_data_token=bk_audit_settings.bk_data_token,
            endpoint=bk_audit_settings.ot_endpoint,
        )
