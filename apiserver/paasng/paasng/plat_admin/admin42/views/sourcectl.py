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
from rest_framework import status
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_admin_audit_record
from paasng.plat_admin.admin42.serializers.sourcectl import SourceTypeSpecConfigSLZ
from paasng.plat_admin.admin42.utils.mixins import GenericTemplateView
from paasng.platform.sourcectl.models import SourceTypeSpecConfig


class SourceTypeSpecManageView(GenericTemplateView):
    """平台服务管理-代码库配置"""

    template_name = "admin42/platformmgr/sourcectl.html"
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    name = "代码库配置"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)

        available_spec_cls = [
            "BkSvnSourceTypeSpec",
            "GitHubSourceTypeSpec",
            "GiteeSourceTypeSpec",
            "BareGitSourceTypeSpec",
            "BareSvnSourceTypeSpec",
            "GitLabSourceTypeSpec",
        ]
        # 存在 TcGitSourceTypeSpec 才将其添加到可选项中
        try:
            from paasng.platform.sourcectl.type_specs import TcGitSourceTypeSpec  # noqa: F401

            available_spec_cls.append("TcGitSourceTypeSpec")
        except ImportError:
            pass

        kwargs.update(
            {
                "paas_doc_url_prefix": settings.PAAS_DOCS_URL_PREFIX,
                "bk_paas_url": settings.BKPAAS_URL,
                "spec_cls_choices": {
                    f"paasng.platform.sourcectl.type_specs.{spec_cls}": spec_cls for spec_cls in available_spec_cls
                },
            }
        )
        return kwargs


class SourceTypeSpecViewSet(ListModelMixin, GenericViewSet):
    """平台服务管理-代码库配置API"""

    queryset = SourceTypeSpecConfig.objects.all()
    serializer_class = SourceTypeSpecConfigSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def create(self, request):
        """创建代码库配置"""
        slz = SourceTypeSpecConfigSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        slz.save()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.SOURCE_TYPE_SPEC,
            attribute=slz.data["name"],
            data_after=DataDetail(data=slz.data),
        )
        return Response(status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """更新代码库配置"""
        source_type_spec = self.get_object()
        data_before = DataDetail(data=SourceTypeSpecConfigSLZ(source_type_spec).data)

        slz = SourceTypeSpecConfigSLZ(source_type_spec, data=request.data)
        slz.is_valid(raise_exception=True)
        slz.save()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.SOURCE_TYPE_SPEC,
            attribute=slz.data["name"],
            data_before=data_before,
            data_after=DataDetail(data=slz.data),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def destroy(self, request, *args, **kwargs):
        """删除代码库配置"""
        source_type_spec = self.get_object()
        data_before = DataDetail(data=SourceTypeSpecConfigSLZ(source_type_spec).data)
        source_type_spec.delete()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.SOURCE_TYPE_SPEC,
            attribute=source_type_spec.name,
            data_before=data_before,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
