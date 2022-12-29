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

from bkapi_client_core.exceptions import APIGatewayResponseError, ResponseError
from django.conf import settings

from paasng.pluginscenter.bk_devops.apigw.client import Client
from paasng.pluginscenter.bk_devops.apigw.client import Group as BkDevopsGroup
from paasng.pluginscenter.bk_devops.exceptions import BkDevopsApiError, BkDevopsGatewayServiceError

logger = logging.getLogger(__name__)


class BkDevopsClient:
    """bk-devops 通过 APIGW 提供的 API"""

    def __init__(self, bk_username: str):
        self.bk_username = bk_username
        # 蓝盾只提供了正式环境的 API
        client = Client(endpoint=settings.BK_API_URL_TMPL, stage="prod")

        client.update_bkapi_authorization(
            **{
                'bk_app_code': settings.BK_APP_CODE,
                'bk_app_secret': settings.BK_APP_SECRET,
            }
        )
        self.client: BkDevopsGroup = client.api

    def _prepare_headers(self) -> dict:
        headers = {
            # 应用态 API 需要添加 X-DEVOPS-UID，用户态 API 不需要
            "X-DEVOPS-UID": self.bk_username,
        }
        return headers

    def get_metrics_summary(self, devops_project_id):
        """
        :param devops_project_id: 蓝盾项目ID
        """
        path_params = {"projectId": devops_project_id}
        try:
            resp = self.client.v4_app_metrics_summary(
                headers=self._prepare_headers(),
                path_params=path_params,
            )
        except (APIGatewayResponseError, ResponseError) as e:
            raise BkDevopsGatewayServiceError(
                f'get stream ci metrics summary (id: {devops_project_id}) error, detail: {e}'
            )

        if resp.get('status') != 0:
            logger.exception(f'get stream ci metrics summary (id: {devops_project_id}) error, resp:{resp}')
            raise BkDevopsApiError(resp['message'])

        return resp['data']['overview']
