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

from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.accessories.ci import serializers
from paasng.accessories.ci.base import BkUserOAuth
from paasng.accessories.ci.clients.bk_ci import BkCIClient
from paasng.accessories.ci.constants import CIBackend
from paasng.accessories.ci.exceptions import NotSupportedRepoType
from paasng.accessories.ci.managers import get_ci_manager_cls_by_backend
from paasng.accessories.ci.models import CIAtomJob, CIResourceAtom
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin

logger = logging.getLogger(__name__)


class CIJobViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """获取 CI 任务
    TODO 前端修改完后删除，包括 url 和 serializers
    """

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @property
    def paginator(self):
        if not hasattr(self, "_paginator"):
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
            CIAtomJob.objects.filter(env__module=module, **filter_params).order_by("-created"), self.request, view=self
        )
        return self.paginator.get_paginated_response(data=serializers.CIAtomJobSerializer(page, many=True).data)


class CIInfoViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """获取 CI 信息"""

    def query(self, request, code, module_name):
        application = self.get_application()
        module = application.get_module(module_name)
        repo = module.get_source_obj()

        # 防御，避免有数据拿不到 source_obj
        if not repo:
            enabled = False
        else:
            try:
                get_ci_manager_cls_by_backend(CIBackend.CODECC).check_repo_support(repo.get_source_type())
                enabled = True
            except NotSupportedRepoType:
                enabled = False

        return Response(data=dict(enabled=enabled))

    @swagger_auto_schema(responses={200: serializers.CodeCCDetailSerializer, 204: None}, tags=["代码检查"])
    def get_detail(self, request, code, module_name):
        application = self.get_application()
        module = application.get_module(module_name)

        # 查询模块下最近一次代码检查记录
        last_ci_atom = CIResourceAtom.objects.filter(env__module=module).order_by("-created").first()
        if not last_ci_atom:
            # 未执行过代码检查，去部署
            return Response(status=status.HTTP_204_NO_CONTENT)

        task_id = last_ci_atom.task_id
        # 详情访问 URL
        detail_url = settings.CODE_CHECK_CONFIGS[CIBackend.CODECC]["base_detail_url"].format(
            project_id=last_ci_atom.resource.credentials["project_id"], task_id=task_id
        )

        # 调用 API 查询代码检查的详细结果
        user_oauth = BkUserOAuth.from_request(request)
        client = BkCIClient(user_oauth)
        data = client.get_codecc_defect_tool_counts(task_id)
        data["detailUrl"] = detail_url

        serializer = serializers.CodeCCDetailSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        return Response(data=serializer.data)
