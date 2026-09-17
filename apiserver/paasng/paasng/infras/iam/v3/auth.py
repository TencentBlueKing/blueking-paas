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
from functools import wraps
from typing import Dict, List, Optional

from django.conf import settings
from django.db.models import Q
from iam import IAM, Action, MultiActionRequest, Request, Resource, Subject
from iam.exceptions import AuthAPIError

from paasng.infras.iam.base.backends import BaseAuthBackend
from paasng.infras.iam.base.dto import AuthResource
from paasng.infras.iam.exceptions import BKIAMAuthCheckError

logger = logging.getLogger(__name__)


def _reraise_as_auth_check_error(func):
    """把 SDK 抛出的 AuthAPIError 转换为平台自身的鉴权异常

    V4 无 SDK，鉴权失败抛的是 BKIAMGatewayServiceError 的子类。两版须对调用方呈现同一种
    异常类型，调用方才能在不感知版本、也不 import SDK 异常的前提下捕获。
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AuthAPIError as e:
            raise BKIAMAuthCheckError(f"request bk-iam auth api failed: {e}") from e

    return wrapper


class BKIAMV3AuthBackend(BaseAuthBackend):
    """基于 bk-iam Python SDK 的 V3 鉴权实现"""

    @_reraise_as_auth_check_error
    def resource_type_allowed(self, username: str, tenant_id: str, action_id: str, use_cache: bool = False) -> bool:
        _iam = self._make_iam(tenant_id)
        request = self._make_request(username, action_id)
        if not use_cache:
            return _iam.is_allowed(request)
        return _iam.is_allowed_with_cache(request)

    @_reraise_as_auth_check_error
    def resource_inst_allowed(
        self,
        username: str,
        tenant_id: str,
        action_id: str,
        resource: AuthResource,
        use_cache: bool = False,
    ) -> bool:
        _iam = self._make_iam(tenant_id)
        request = self._make_request(username, action_id, resources=[self._to_sdk_resource(resource)])
        if not use_cache:
            return _iam.is_allowed(request)
        return _iam.is_allowed_with_cache(request)

    @_reraise_as_auth_check_error
    def resource_inst_multi_actions_allowed(
        self, username: str, tenant_id: str, action_ids: List[str], resource: AuthResource
    ) -> Dict[str, bool]:
        actions = [Action(action_id) for action_id in action_ids]
        request = MultiActionRequest(
            settings.IAM_PAAS_V3_SYSTEM_ID,
            Subject("user", username),
            actions,
            [self._to_sdk_resource(resource)],
            None,
        )
        return self._make_iam(tenant_id).resource_multi_actions_allowed(request)

    def build_resource_filter(
        self, username: str, tenant_id: str, action_id: str, key_mapping: Optional[Dict[str, str]] = None
    ) -> Optional[Q]:
        request = self._make_request(username, action_id)
        try:
            return self._make_iam(tenant_id).make_filter(request, key_mapping=key_mapping)
        except AuthAPIError as e:
            logger.warning("build resource filter for action %s failed: %s", action_id, e)
            return None

    @staticmethod
    def _to_sdk_resource(resource: AuthResource) -> Resource:
        return Resource(resource.system, resource.type, resource.id, resource.attribute)

    @staticmethod
    def _make_request(username: str, action_id: str, resources: Optional[List[Resource]] = None) -> Request:
        return Request(settings.IAM_PAAS_V3_SYSTEM_ID, Subject("user", username), Action(action_id), resources, None)

    @staticmethod
    def _make_iam(tenant_id: str) -> IAM:
        return IAM(
            settings.IAM_APP_CODE,
            settings.IAM_APP_SECRET,
            settings.BK_IAM_APIGATEWAY_URL,
            bk_tenant_id=tenant_id,
        )
