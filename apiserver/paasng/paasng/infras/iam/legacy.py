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

# PaaS 2.0 相关权限
import logging

from blue_krill.data_types.enum import EnumField, StrStructuredEnum
from django.conf import settings
from iam import IAM, Action, Request, Subject
from iam.contrib.converter.sql import SQLConverter
from iam.exceptions import AuthAPIError

from paasng.core.tenant.user import get_init_tenant_id

logger = logging.getLogger(__name__)


class LegacyAction(StrStructuredEnum):
    DEVELOP_APP = EnumField("develop_app", label="开发 SaaS 应用及外链应用")
    MANAGE_SMART = EnumField("manage_smart", label="管理 S-mart 应用")


class Permission:
    def __init__(self):
        self._iam = IAM(
            settings.IAM_APP_CODE,
            settings.IAM_APP_SECRET,
            settings.BK_IAM_APIGATEWAY_URL,
            bk_tenant_id=get_init_tenant_id(),
        )

    def allowed_manage_smart(self, username):
        """smart管理权限"""
        try:
            request = self._make_request_without_resources(username, LegacyAction.MANAGE_SMART)
            return self._iam.is_allowed_with_cache(request)
        except AuthAPIError:
            logger.exception("check is allowed to manage smart app error.")
            return False

    def app_filters(self, username):
        """用户有权限的应用列表，拉回策略, 自己算!"""
        request = self._make_request_without_resources(username, LegacyAction.DEVELOP_APP)

        # 两种策略 1) 实例级别 2) 用户级别，只有条件 code in []
        key_mapping = {"app.id": "paas_app.code"}

        try:
            filters = self._iam.make_filter(request, converter_class=SQLConverter, key_mapping=key_mapping)
        except AuthAPIError:
            return None

        # NOTE: paas 2.0 应用无租户概念，暂时不需要考虑租户过滤问题
        return filters

    @staticmethod
    def _make_request_without_resources(username: str, action_id: str) -> "Request":
        return Request(settings.IAM_SYSTEM_ID, Subject("user", username), Action(action_id), None, None)
