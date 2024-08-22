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

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.audit import constants
from paasng.misc.audit.service import DataDetail, add_admin_audit_record
from paasng.plat_admin.admin42.serializers.config_vars import ConfigVarSLZ
from paasng.plat_admin.admin42.serializers.module import ModuleSLZ
from paasng.plat_admin.admin42.views.applications import ApplicationDetailBaseView
from paasng.platform.engine.constants import ConfigVarEnvName
from paasng.platform.engine.models.config_var import ConfigVar
from paasng.platform.engine.views import ConfigVarViewSet as BaseConfigVarViewSet

logger = logging.getLogger(__name__)


class ConfigVarManageView(ApplicationDetailBaseView):
    name = "环境变量管理"
    template_name = "admin42/applications/detail/engine/config_var.html"

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
    permission_classes = [
        IsAuthenticated,
        site_perm_class(SiteAction.MANAGE_PLATFORM),
        application_perm_class(AppAction.BASIC_DEVELOP),
    ]

    def get_queryset(self):
        application = self.get_application()
        queryset = ConfigVar.objects.filter(module__in=application.modules.all()).order_by("module__is_default")
        return queryset

    def create(self, request, *args, **kwargs):
        """创建应用内环境变量"""
        data_after = DataDetail(type=constants.DataType.RAW_DATA, data=copy.deepcopy(request.data))
        slz = self.get_serializer(data=request.data)
        slz.is_valid(raise_exception=True)
        slz.save()
        add_admin_audit_record(
            user=request.user.pk,
            operation=constants.OperationEnum.CREATE_APP_ENV_VAR,
            target=constants.OperationTarget.APP,
            app_code=self._get_param_from_kwargs(["code", "app_code"]),
            module_name=slz.validated_data.get("module").name,
            environment=slz.validated_data.get("environment_name"),
            data_after=data_after,
        )
        return Response(slz.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """删除应用内环境变量"""
        instance = self.get_object()
        data_before = DataDetail(
            type=constants.DataType.RAW_DATA,
            data={"key": instance.key, "value": instance.value, "description": instance.description},
        )
        instance.delete()
        add_admin_audit_record(
            user=request.user.pk,
            operation=constants.OperationEnum.DELETE_APP_ENV_VAR,
            target=constants.OperationTarget.APP,
            app_code=self._get_param_from_kwargs(["code", "app_code"]),
            module_name=instance.module.name,
            environment=instance.environment.environment,
            data_before=data_before,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        """更新应用内环境变量"""
        instance = self.get_object()
        slz = self.get_serializer(instance=instance, data=request.data)
        slz.is_valid(raise_exception=True)
        data_before = DataDetail(
            type=constants.DataType.RAW_DATA,
            data={"key": instance.key, "value": instance.value, "description": instance.description},
        )
        slz.save()
        add_admin_audit_record(
            user=request.user.pk,
            operation=constants.OperationEnum.MODIFY_APP_ENV_VAR,
            target=constants.OperationTarget.APP,
            app_code=self._get_param_from_kwargs(["code", "app_code"]),
            module_name=instance.module.name,
            environment=instance.environment.environment,
            data_before=data_before,
            data_after=DataDetail(
                type=constants.DataType.RAW_DATA,
                data={"key": instance.key, "value": instance.value, "description": instance.description},
            ),
        )
        return Response(slz.data)
