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
from typing import Any, Dict, Optional

from bkapi_client_core.apigateway import Operation
from django.utils.crypto import get_random_string
from requests import Response

from paas_wl.resources.base.bcs_client import BCSClient


class StubBCSClient(BCSClient):
    def handle_request(self, operation: Operation, context: Dict[str, Any]) -> Optional[Response]:
        return Response()

    def parse_response(self, operation: Operation, response: Optional[Response]) -> Any:
        if operation.name == 'create_web_console_sessions':
            session_id = get_random_string(32)
            return {
                'code': 0,
                'data': {
                    'session_id': session_id,
                    'web_console_url': f'http://example.com/web_console/'
                    f'?session_id={session_id}&container_name={get_random_string(8)}',
                },
            }
        return {}
