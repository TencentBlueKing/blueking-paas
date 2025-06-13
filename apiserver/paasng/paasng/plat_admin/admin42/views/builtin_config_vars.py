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
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.core.region.models import get_all_regions
from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_admin_audit_record
from paasng.plat_admin.admin42.serializers.config_vars import (
    BuiltinConfigVarCreateInputSLZ,
    BuiltinConfigVarListOutputSLZ,
    BuiltinConfigVarUpdateInputSLZ,
)
from paasng.plat_admin.admin42.utils.mixins import GenericTemplateView
from paasng.platform.engine.models.config_var import BuiltinConfigVar


class BuiltinConfigVarView(GenericTemplateView):
    name = "环境变量管理"
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    template_name = "admin42/platformmgr/builtin_config_vars.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["system_prefix"] = settings.CONFIGVAR_SYSTEM_PREFIX
        context["regions"] = list(get_all_regions().keys())
        return context

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class BuiltinConfigVarViewSet(viewsets.GenericViewSet):
    """环境变量管理 API 接口"""

    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def list(self, request):
        config_vars = BuiltinConfigVar.objects.order_by("-updated")
        return Response(BuiltinConfigVarListOutputSLZ(config_vars, many=True).data)

    def create(self, request):
        slz = BuiltinConfigVarCreateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        BuiltinConfigVar.objects.create(
            key=data["key"],
            value=data["value"],
            description=data["description"],
            operator=request.user,
        )

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.ENV_VAR,
            attribute=data["key"],
            data_after=DataDetail(
                data={"key": data["key"], "value": data["value"], "description": data["description"]},
            ),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, pk):
        slz = BuiltinConfigVarUpdateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        config_var = get_object_or_404(BuiltinConfigVar, pk=pk)
        data_before = DataDetail(
            data={"key": config_var.key, "value": config_var.value, "description": config_var.description},
        )

        config_var.value = data["value"]
        config_var.description = data["description"]
        config_var.operator = request.user
        config_var.save(update_fields=["value", "description", "operator", "updated"])

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.ENV_VAR,
            attribute=config_var.key,
            data_before=data_before,
            data_after=DataDetail(
                data={"key": config_var.key, "value": data["value"], "description": data["description"]},
            ),
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    def destroy(self, request, pk):
        config_var = get_object_or_404(BuiltinConfigVar, pk=pk)
        config_var.delete()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.ENV_VAR,
            attribute=config_var.key,
            data_before=DataDetail(
                data={"key": config_var.key, "value": config_var.value, "description": config_var.description},
            ),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
