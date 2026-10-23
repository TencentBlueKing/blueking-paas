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
from typing import List

from django.conf import settings
from iam import IAM
from iam.apply import models

from paasng.infras.iam.base.constants import IAMVersion
from paasng.infras.iam.exceptions import BKIAMGatewayServiceError
from paasng.infras.iam.shim import get_iam_version

from .request import ActionResourcesRequest

logger = logging.getLogger(__name__)


class ApplyURLGenerator:
    @classmethod
    def generate_apply_url(cls, tenant_id: str, action_request_list: List[ActionResourcesRequest]) -> str:
        """
        生成权限申请跳转 url

        参考 https://github.com/TencentBlueKing/iam-python-sdk/blob/master/docs/usage.md#14-获取无权限申请跳转url
        """
        if get_iam_version() == IAMVersion.V4:
            return cls._generate_v4_apply_url(tenant_id, action_request_list)
        return cls._generate_v3_apply_url(tenant_id, action_request_list)

    @classmethod
    def _generate_v3_apply_url(cls, tenant_id: str, action_request_list: List[ActionResourcesRequest]) -> str:
        app = cls._make_application(action_request_list)
        _iam = IAM(
            settings.IAM_APP_CODE,
            settings.IAM_APP_SECRET,
            settings.BK_IAM_APIGATEWAY_URL,
            bk_tenant_id=tenant_id,
        )
        ok, message, url = _iam.get_apply_url(app)
        if not ok:
            logger.error("generate_apply_url from bkiam v3 failed: %s", message)
            return settings.BK_IAM_EFFECTIVE_URL
        return url

    @staticmethod
    def _generate_v4_apply_url(tenant_id: str, action_request_list: List[ActionResourcesRequest]) -> str:
        from paasng.infras.iam.v4.apply_url import fetch_apply_url

        try:
            return fetch_apply_url(tenant_id, action_request_list)
        except BKIAMGatewayServiceError:
            logger.exception("generate_apply_url from bkiam v4 failed")
            return settings.BK_IAM_EFFECTIVE_URL

    @staticmethod
    def _make_application(action_request_list: List[ActionResourcesRequest]) -> models.Application:
        """为 generate_apply_url 方法生成 models.Application"""
        return models.Application(
            settings.IAM_PAAS_V3_SYSTEM_ID, actions=[req.to_action() for req in action_request_list]
        )
