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

import copy
import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_admin_audit_record
from paasng.plat_admin.admin42.serializers.config_vars import ConfigVarSLZ
from paasng.plat_admin.admin42.serializers.module import ModuleSLZ
from paasng.plat_admin.admin42.views.applications import ApplicationDetailBaseView
from paasng.platform.applications.models import Application
from paasng.platform.engine.constants import ConfigVarEnvName
from paasng.platform.engine.models.config_var import ENVIRONMENT_ID_FOR_GLOBAL, ENVIRONMENT_NAME_FOR_GLOBAL, ConfigVar
from paasng.platform.engine.views import ConfigVarViewSet as BaseConfigVarViewSet

logger = logging.getLogger(__name__)


class ConfigVarManageView(ApplicationDetailBaseView):
    name = "环境变量管理"
    template_name = "admin42/operation/applications/detail/engine/config_var.html"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        application = self.get_application()
        config_vars = ConfigVarSLZ(
            ConfigVar.objects.filter(module__in=application.modules.all()).order_by("module__is_default"), many=True
        ).data
        kwargs["config_vars"] = config_vars
        kwargs["env_choices"] = [{"value": value, "text": text} for value, text in ConfigVarEnvName.get_choices()]
        kwargs["module_list"] = ModuleSLZ(application.modules.all(), many=True).data
        return kwargs


class ConfigVarViewSet(BaseConfigVarViewSet):
    schema = None
    serializer_class = ConfigVarSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def get_queryset(self):
        application = get_object_or_404(Application, code=self.kwargs["code"])
        queryset = ConfigVar.objects.filter(module__in=application.modules.all()).order_by("module__is_default")
        return queryset

    def get_serializer_context(self):
        application = get_object_or_404(Application, code=self.kwargs["code"])
        module_name = self._get_param_from_kwargs(["module_name"])
        context = {"module": application.get_module(module_name)}
        return context

    @staticmethod
    def _gen_data_detail(config_var: ConfigVar) -> DataDetail:
        return DataDetail(
            data={"key": config_var.key, "value": config_var.value, "description": config_var.description},
        )

    def create(self, request, *args, **kwargs):
        """创建应用内环境变量"""
        data_after = DataDetail(data=copy.deepcopy(request.data))
        slz = self.get_serializer(data=request.data)
        slz.is_valid(raise_exception=True)
        slz.save()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.ENV_VAR,
            app_code=self.kwargs["code"],
            module_name=slz.validated_data.get("module").name,
            environment=request.data["environment_name"],
            data_after=data_after,
        )
        return Response(slz.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """更新应用内环境变量"""
        config_var = self.get_object()
        data_before = self._gen_data_detail(config_var)
        slz = self.get_serializer(instance=config_var, data=request.data)
        slz.is_valid(raise_exception=True)
        slz.save()

        env = ENVIRONMENT_NAME_FOR_GLOBAL
        if config_var.environment_id != ENVIRONMENT_ID_FOR_GLOBAL:
            env = config_var.environment.environment
        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.ENV_VAR,
            app_code=self.kwargs["code"],
            module_name=config_var.module.name,
            environment=env,
            data_before=data_before,
            data_after=self._gen_data_detail(config_var),
        )
        return Response(slz.data)

    def destroy(self, request, *args, **kwargs):
        """删除应用内环境变量"""
        config_var = self.get_object()
        data_before = self._gen_data_detail(config_var)
        config_var.delete()

        env = ENVIRONMENT_NAME_FOR_GLOBAL
        if config_var.environment_id != ENVIRONMENT_ID_FOR_GLOBAL:
            env = config_var.environment.environment
        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.ENV_VAR,
            app_code=self.kwargs["code"],
            module_name=config_var.module.name,
            environment=env,
            data_before=data_before,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
