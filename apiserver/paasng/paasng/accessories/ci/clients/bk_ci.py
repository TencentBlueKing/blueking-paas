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
from typing import TYPE_CHECKING

from bkapi_client_core.exceptions import APIGatewayResponseError
from django.conf import settings

from paasng.accessories.ci.clients.apigw import Client
from paasng.accessories.ci.clients.apigw import Group as BKCIGroup
from paasng.accessories.ci.clients.exceptions import BKCIApiError, BKCIGatewayServiceError

if TYPE_CHECKING:
    from paasng.accessories.ci.base import BkUserOAuth

logger = logging.getLogger(__name__)


class BkCIClient:
    """蓝盾通过 APIGW 提供的应用态 API"""

    def __init__(self, user_oauth: 'BkUserOAuth'):
        self.user_oauth = user_oauth
        # 蓝盾只提供了正式环境的 API
        client = Client(endpoint=settings.BK_API_URL_TMPL, stage="prod")

        client.update_bkapi_authorization(
            bk_app_code=settings.BK_APP_CODE,
            bk_app_secret=settings.BK_APP_SECRET,
        )

        client.update_headers(
            {
                # 应用态 API 需要添加 X-DEVOPS-UID
                "X-DEVOPS-UID": self.user_oauth.operator,
            }
        )

        self.client: BKCIGroup = client.api

    def trigger_codecc_pipeline(self, trigger_params: dict):
        """[应用态]手动触发流水线，不存在时创建"""
        try:
            resp = self.client.app_codecc_custom_pipeline_new(data=trigger_params)
        except APIGatewayResponseError as e:
            raise BKCIGatewayServiceError(f'trigger codecc pipeline error, detail: {e}')

        # API 返回示例，code 是字符串格式
        # {u'status': 200, u'message': u'The system is busy inside. Please try again later', u'code': u'2300001'}
        if resp.get('code') != '0':
            logger.exception(f"trigger codecc pipeline error, resp:{resp}")
            raise BKCIApiError(resp['message'], resp['code'])

        return resp

    def get_codecc_defect_tool_counts(self, task_id: int):
        """[应用态]根据任务id查询所有工具问题数"""
        try:
            resp = self.client.app_codecc_tool_defect_count(data={"taskId": task_id})
        except APIGatewayResponseError as e:
            raise BKCIGatewayServiceError(f'get codecc defect tool counts error, detail: {e}')

        if resp.get('code') != '0':
            logger.exception(f"get codecc defect tool counts error, resp:{resp}")
            raise BKCIApiError(resp['message'], resp['code'])

        return resp.get('data')

    def get_codecc_taskinfo_by_build_id(self, build_id: str):
        """[应用态]根据codeccBuildId查询buildId映射"""
        try:
            resp = self.client.app_codecc_build_id_mapping(data={"codeccbuildId": build_id})
        except APIGatewayResponseError as e:
            raise BKCIGatewayServiceError(f'get codecc task info by build({build_id}) error, detail: {e}')

        if resp.get('code') != '0':
            logger.exception(f"get codecc task info, resp:{resp}")
            raise BKCIApiError(resp['message'], resp['code'])

        return resp.get('data', {}).get('task_id')
