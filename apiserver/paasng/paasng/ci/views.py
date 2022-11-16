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
import logging

from rest_framework import viewsets
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated

from paasng.accessories.iam.permissions.resources.application import AppAction
from paasng.accounts.permissions.application import application_perm_class
from paasng.ci import serializers
from paasng.ci.models import CIAtomJob
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin

logger = logging.getLogger(__name__)


class CIJobViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """获取 CI 任务"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @property
    def paginator(self):
        if not hasattr(self, '_paginator'):
            self._paginator = LimitOffsetPagination()
            self._paginator.default_limit = 10
        return self._paginator

    def list(self, request, code, module_name):
        application = self.get_application()
        module = application.get_module(module_name)

        serializer = serializers.CIAtomJobListSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        filter_params = dict()
        for _filter_key in ["backend", "status"]:
            _filter_value = serializer.validated_data.get(_filter_key, None)
            if _filter_value:
                filter_params[_filter_key] = _filter_value

        page = self.paginator.paginate_queryset(
            CIAtomJob.objects.filter(env__module=module, **filter_params).order_by('-created'), self.request, view=self
        )
        return self.paginator.get_paginated_response(data=serializers.CIAtomJobSerializer(page, many=True).data)
