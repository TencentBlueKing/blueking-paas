# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from django.conf import settings
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.accessories.bk_lesscode.client import make_bk_lesscode_client
from paasng.accounts.permissions.application import application_perm_class
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.modules.constants import SourceOrigin


class LesscodeModuleViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class('view_application')]

    def retrieve(self, request, code, module_name):
        """查询模块在 lesscode 平台上对应的访问地址"""
        application = self.get_application()
        module = application.get_module(module_name)

        address_in_lesscode = ''
        if module.source_origin == SourceOrigin.BK_LESS_CODE:
            bk_token = request.COOKIES.get(settings.BK_COOKIE_NAME, None)
            address_in_lesscode = make_bk_lesscode_client(login_cookie=bk_token).get_address(
                application.code, module.name
            )

        return Response(data={'address_in_lesscode': address_in_lesscode, 'tips': settings.BK_LESSCODE_TIPS})
