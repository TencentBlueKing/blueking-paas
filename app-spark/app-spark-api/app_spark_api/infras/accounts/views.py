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

from django.conf import settings
from django.template.response import TemplateResponse
from django.views import View

from app_spark_api.utils.urls import reverse_public


class HomeView(View):
    def get(self, request):
        # reverse_public() includes FORCE_SCRIPT_NAME so the browser calls the API
        # under the ingress prefix. reverse() itself is not enough: this is a sync
        # view served over ASGI, and the thread-local script prefix does not follow.
        return TemplateResponse(
            request,
            "accounts/home.html",
            {
                "api_userinfo_url": reverse_public("api:accounts-userinfo"),
                "default_login_url": settings.LOGIN_FULL,
            },
        )
