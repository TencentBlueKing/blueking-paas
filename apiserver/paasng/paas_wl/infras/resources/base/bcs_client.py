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
import json
from typing import Any, Dict

from bkapi_client_core.apigateway import APIGatewayClient, Operation, OperationGroup, bind_property
from django.conf import settings


class AuthOperation(Operation):
    """头部带有认证信息的 Operation"""

    def _get_context(self, **kwargs) -> Dict[str, Any]:
        """将认证信息添加到 headers"""
        context = super()._get_context(**kwargs)

        headers = context.get("headers") or {}
        headers.update(
            {
                "X-Bkapi-Authorization": json.dumps(
                    {"bk_app_code": settings.BK_APP_CODE, "bk_app_secret": settings.BK_APP_SECRET}
                ),
                "Content-Type": "application/json",
            }
        )

        context["headers"] = headers
        return context


class Group(OperationGroup):
    # 创建 websocket session
    create_web_console_sessions = bind_property(
        AuthOperation,
        name="create_web_console_sessions",
        method="POST",
        path="/{version}/webconsole/api/portal/projects/{project_id_or_code}/"
        "clusters/{cluster_id}/web_console/sessions/",
    )


class BCSClient(APIGatewayClient):
    """bcs-services 提供的网关 client"""

    _api_name = "bcs-api-gateway"
    api = bind_property(Group, name="api")

    def __init__(self):
        super().__init__(stage=settings.APIGW_ENVIRONMENT, endpoint=settings.BK_API_URL_TMPL)
