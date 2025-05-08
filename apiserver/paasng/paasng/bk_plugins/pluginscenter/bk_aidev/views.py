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

from django.conf import settings
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from paasng.bk_plugins.pluginscenter.bk_aidev.client import BkAIDevClient
from paasng.bk_plugins.pluginscenter.bk_aidev.serializers import BkAIDevSpaceSLZ
from paasng.core.tenant.user import get_tenant


class BkAIDevManageView(ViewSet):
    def get_spaces(self, request):
        login_cookie = request.COOKIES.get(settings.BK_COOKIE_NAME, None)
        tenant_id = get_tenant(request.user).id
        client = BkAIDevClient(login_cookie, tenant_id)
        data = client.list_spaces()
        return Response(BkAIDevSpaceSLZ(data, many=True).data)
