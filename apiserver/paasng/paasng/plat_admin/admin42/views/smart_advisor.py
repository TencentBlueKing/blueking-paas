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
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin, ListModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from paasng.accessories.smart_advisor.models import DeployFailurePattern, DocumentaryLink
from paasng.accounts.permissions.constants import SiteAction
from paasng.accounts.permissions.global_site import site_perm_class
from paasng.plat_admin.admin42.serializers.smart_advisor import DeployFailurePatternSLZ, DocumentaryLinkSLZ
from paasng.plat_admin.admin42.utils.mixins import GenericTemplateView


class DocumentaryLinkView(GenericTemplateView):
    """文档链接管理页"""

    template_name = "admin42/platformmgr/documentary_link.html"
    queryset = DocumentaryLink.objects.all()
    serializer_class = DocumentaryLinkSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    name = "文档管理"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)

        kwargs["documents"] = data = self.list(self.request, *self.args, **self.kwargs)
        kwargs['pagination'] = self.get_pagination_context(self.request)
        return kwargs


class DocumentaryLinkManageViewSet(
    CreateModelMixin, DestroyModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet
):
    """智能顾问-文档管理API"""

    serializer_class = DocumentaryLinkSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    queryset = DocumentaryLink.objects.all()


class DeployFailurePatternView(GenericTemplateView):
    """失败提示管理"""

    template_name = "admin42/platformmgr/deploy_failure_tips.html"
    queryset = DeployFailurePattern.objects.all()
    serializer_class = DeployFailurePatternSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    name = "失败提示管理"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)

        kwargs["failure_tips"] = data = self.list(self.request, *self.args, **self.kwargs)
        kwargs['pagination'] = self.get_pagination_context(self.request)
        return kwargs


class DeployFailurePatternManageViewSet(
    CreateModelMixin, DestroyModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet
):
    """智能顾问-失败提示管理API"""

    serializer_class = DeployFailurePatternSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    queryset = DeployFailurePattern.objects.all()
