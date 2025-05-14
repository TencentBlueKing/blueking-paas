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

import logging
from typing import List

from django.conf import settings
from iam import IAM
from iam.apply import models

from .request import ActionResourcesRequest

logger = logging.getLogger(__name__)


class ApplyURLGenerator:
    iam = IAM(
        settings.IAM_APP_CODE,
        settings.IAM_APP_SECRET,
        settings.BK_IAM_V3_INNER_URL,
        settings.BK_PAAS2_URL,
        settings.BK_IAM_APIGATEWAY_URL,
    )

    @classmethod
    def generate_apply_url(cls, username: str, action_request_list: List[ActionResourcesRequest]) -> str:
        """
        生成权限申请跳转 url

        参考 https://github.com/TencentBlueKing/iam-python-sdk/blob/master/docs/usage.md#14-获取无权限申请跳转url
        """
        app = cls._make_application(action_request_list)
        ok, message, url = cls.iam.get_apply_url(app, bk_username=username)
        if not ok:
            logger.error("generate_apply_url failed: %s", message)
            return settings.BK_IAM_URL
        return url

    @staticmethod
    def _make_application(action_request_list: List[ActionResourcesRequest]) -> models.Application:
        """为 generate_apply_url 方法生成 models.Application"""
        return models.Application(
            settings.IAM_PAAS_V3_SYSTEM_ID, actions=[req.to_action() for req in action_request_list]
        )
