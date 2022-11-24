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
from django.conf import settings

from paas_wl.utils.local import local


class RequestIDProvider:
    """向 request，response 注入 request_id"""

    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        local.request = request
        request.request_id = local.get_http_request_id()

        response = self.get_response(request)
        response[settings.REQUEST_ID_HEADER_KEY] = request.request_id

        local.release()
        return response
