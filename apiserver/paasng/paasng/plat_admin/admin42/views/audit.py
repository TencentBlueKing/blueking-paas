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

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class
from paasng.misc.audit.constants import AccessType, OperationEnum, OperationTarget, ResultCode
from paasng.misc.audit.models import AdminOperationRecord
from paasng.plat_admin.admin42.serializers.audit import (
    AppAuditOperationListInputSLZ,
    AppAuditOperationListOutputSLZ,
    AppAuditOperationRetrieveOutputSLZ,
    AuditOperationListOutputSLZ,
    AuditOperationRetrieveOutputSLZ,
)
from paasng.plat_admin.admin42.utils.mixins import GenericTemplateView
from paasng.platform.engine.constants import ConfigVarEnvName


class AdminOperationAuditManageView(GenericTemplateView):
    """后台管理审计页面"""

    name = "后台管理审计"
    queryset = AdminOperationRecord.objects.filter(app_code=None).order_by("-start_time")
    serializer_class = AuditOperationListOutputSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    template_name = "admin42/audit/admin_operation_audit.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["audit_records"] = self.list(self.request, *self.args, **self.kwargs)
        context["pagination"] = self.get_pagination_context(self.request)
        context["result_types"] = dict(ResultCode.get_choices())
        context["access_types"] = dict(AccessType.get_choices())
        context["target_types"] = dict(OperationTarget.get_choices())
        context["operation_types"] = dict(OperationEnum.get_choices())
        return context


class AdminOperationAuditViewSet(generics.RetrieveAPIView):
    """获取单个 AdminOperationRecord 信息，该记录不是 app 操作"""

    serializer_class = AuditOperationRetrieveOutputSLZ
    queryset = AdminOperationRecord.objects.all()
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]


class AdminAppOperationAuditManageView(GenericTemplateView):
    """应用操作审计页面"""

    name = "应用操作审计"
    queryset = AdminOperationRecord.objects.exclude(app_code=None).order_by("-start_time")
    serializer_class = AppAuditOperationListOutputSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    template_name = "admin42/audit/admin_app_operation_audit.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["app_audit_records"] = self.list(self.request, *self.args, **self.kwargs)
        context["pagination"] = self.get_pagination_context(self.request)
        context["result_types"] = dict(ResultCode.get_choices())
        context["access_types"] = dict(AccessType.get_choices())
        context["target_types"] = dict(OperationTarget.get_choices())
        context["operation_types"] = dict(OperationEnum.get_choices())
        context["env_types"] = dict(ConfigVarEnvName.get_choices())
        return context

    def filter_queryset(self, queryset):
        slz = AppAuditOperationListInputSLZ(data=self.request.query_params)
        slz.is_valid(raise_exception=True)
        if filter_key := slz.validated_data["filter_key"]:
            queryset = queryset.filter(app_code__icontains=filter_key)
        return queryset


class AdminAppOperationAuditViewSet(generics.RetrieveAPIView):
    """获取单个 AdminOperationRecord 信息，该记录是 app 操作"""

    serializer_class = AppAuditOperationRetrieveOutputSLZ
    queryset = AdminOperationRecord.objects.all()
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
