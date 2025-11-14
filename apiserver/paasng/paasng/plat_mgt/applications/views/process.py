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

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.plat_mgt.applications.serializers.process import ProcessResourcesInputSLZ, ProcessResourcesOutputSLZ
from paasng.platform.applications.models import Application
from paasng.platform.bkapp_model.models import ModuleProcessSpec, ProcessSpecEnvOverlay
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.models import Module
from paasng.utils.error_codes import error_codes


class ApplicationProcessViewSet(viewsets.GenericViewSet):
    """平台管理 - 进程管理资源限制"""

    queryset = Application.objects.all()
    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    def retrieve(self, request, app_code, module_name):
        """获取当前模块的进程配置的资源限制"""
        application = get_object_or_404(self.get_queryset(), code=app_code)
        try:
            module = application.get_module(module_name)
        except Module.DoesNotExist:
            raise Http404

        proc_specs = []
        for spec in ModuleProcessSpec.objects.filter(module=module):
            data = {
                "name": spec.name,
                "env_overlay": {
                    environment_name.value: {
                        "plan_name": spec.get_plan_name(environment_name),
                        "resources": spec.get_resources(environment_name),
                    }
                    for environment_name in AppEnvName
                },
            }

            proc_specs.append(data)

        return Response(ProcessResourcesOutputSLZ(proc_specs, many=True).data)

    def batch_update(self, request, app_code, module_name):
        """更新模块下进程的资源限制配置"""
        application = get_object_or_404(self.get_queryset(), code=app_code)
        try:
            module: Module = application.get_module(module_name)
        except Module.DoesNotExist:
            raise Http404

        # 只能修改镜像应用和 smart 应用
        if module.source_origin not in [
            SourceOrigin.S_MART,
            SourceOrigin.IMAGE_REGISTRY,
            SourceOrigin.CNATIVE_IMAGE,
            SourceOrigin.AI_AGENT,
        ]:
            raise error_codes.CANNOT_OPERATE_PROCESS.f(_("不支持该应用类型的进程资源配置修改"))

        serializer = ProcessResourcesInputSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        proc_spec = ModuleProcessSpec.objects.get(module=module, name=validated_data["name"])

        for env_name, proc_env_overlay in validated_data["env_overlay"].items():
            plan_name = proc_env_overlay.get("plan_name")
            resources = proc_env_overlay.get("resources")

            # 根据 plan_name 的值决定更新策略
            defaults = {}
            if plan_name == "custom":
                # 自定义方案：只更新 resources，不修改 plan_name
                if resources is not None:
                    defaults["resources"] = resources
            elif plan_name:
                # 预设方案：更新 plan_name，清空 resources
                defaults["plan_name"] = plan_name
                defaults["resources"] = None

            # 只有当有内容需要更新时才调用 update_or_create
            if defaults:
                ProcessSpecEnvOverlay.objects.update_or_create(
                    proc_spec=proc_spec,
                    environment_name=env_name,
                    defaults=defaults,
                )

        return self.retrieve(request, app_code, module_name)
