# -*- coding: utf-8 -*-
import json
from typing import Any, Dict

from bkapi_client_core.apigateway import APIGatewayClient, Operation, OperationGroup, bind_property
from django.conf import settings


class AuthOperation(Operation):
    """头部带有认证信息的 Operation"""

    def _get_context(self, **kwargs) -> Dict[str, Any]:
        """将认证信息添加到 headers"""
        context = super()._get_context(**kwargs)

        headers = context.get('headers') or {}
        headers.update(
            {
                'X-Bkapi-Authorization': json.dumps(
                    {'bk_app_code': settings.BK_APP_CODE, 'bk_app_secret': settings.BK_APP_SECRET}
                ),
                'Content-Type': 'application/json',
            }
        )

        context['headers'] = headers
        return context


class Group(OperationGroup):
    # 创建 websocket session
    create_web_console_sessions = bind_property(
        AuthOperation,
        name='create_web_console_sessions',
        method='POST',
        path='/{version}/webconsole/api/portal/projects/{project_id_or_code}/'
        'clusters/{cluster_id}/web_console/sessions/',
    )


class BCSClient(APIGatewayClient):
    """bcs-services 提供的网关 client"""

    _api_name = 'bcs-api-gateway'
    api = bind_property(Group, name='api')

    def __init__(self):
        super().__init__(stage=settings.APIGW_ENVIRONMENT, endpoint=settings.BK_API_URL_TMPL)
