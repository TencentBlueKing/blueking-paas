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


from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.infras.accounts.permissions.constants import PlatMgtAction
from paasng.infras.accounts.permissions.plat_mgt import plat_mgt_perm_class
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_plat_mgt_audit_record
from paasng.plat_mgt.applications.serializers import (
    ModuleProcessSpecOutputSLZ,
    ProcessSpecInputSLZ,
)
from paasng.platform.applications.models import Application
from paasng.platform.bkapp_model.models import ModuleProcessSpec, ProcessSpecEnvOverlay, ResQuotaPlan
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.modules.constants import SourceOrigin


class ApplicationProcessViewSet(viewsets.GenericViewSet):
    """平台管理 - 应用进程 API"""

    queryset = Application.objects.all()
    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat_mgt.process"],
        operation_description="获取模块的进程资源限制",
        responses={status.HTTP_200_OK: ModuleProcessSpecOutputSLZ()},
    )
    def list_resource(self, request, app_code, module_name):
        """获取模块的进程资源限制"""
        application = get_object_or_404(self.get_queryset(), code=app_code)
        module = get_object_or_404(application.modules, name=module_name)

        proc_specs = ModuleProcessSpec.objects.filter(module=module).prefetch_related("env_overlays")

        # 构建进程列表
        processes = []
        for spec in proc_specs:
            # 构建环境覆盖配置
            overlays_map = {o.environment_name: o for o in spec.env_overlays.all()}
            env_overlays = {
                env_name: {
                    "plan_name": overlay.plan_name,
                    "override_proc_res": (
                        {"plan": overlay.override_plan_name}
                        if overlay.override_plan_name
                        else overlay.override_resources
                    ),
                }
                for env_name in AppEnvName.get_values()
                if (overlay := overlays_map.get(env_name))
            }
            processes.append(
                {
                    "name": spec.name,
                    "plan_name": spec.plan_name,
                    "env_overlays": env_overlays,
                }
            )

        result = {
            "module_name": module_name,
            "source_origin": module.source_origin,
            "processes": processes,
        }
        return Response(ModuleProcessSpecOutputSLZ(result).data)

    @swagger_auto_schema(
        tags=["plat_mgt.process"],
        operation_description="更新单个进程的资源限制",
        request_body=ProcessSpecInputSLZ(),
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def update_resource(self, request, app_code, module_name, process_name):
        """更新单个进程的资源限制"""
        application = get_object_or_404(self.get_queryset(), code=app_code)
        slz = ProcessSpecInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        # 校验 module 的 source_origin 是否可以修改
        module = get_object_or_404(application.modules, name=module_name)
        if module.source_origin != SourceOrigin.S_MART.value:
            return Response(
                {"detail": _("当前仅支持 SMart 应用修改进程资源配额")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 获取进程规格
        try:
            proc_spec = ModuleProcessSpec.objects.prefetch_related("env_overlays").get(
                module=module, name=process_name
            )
        except ModuleProcessSpec.DoesNotExist:
            return Response({"detail": _(f"进程 {process_name} 不存在")}, status=status.HTTP_404_NOT_FOUND)
        # 构建环境覆盖映射
        env_overlays_map = {o.environment_name: o for o in proc_spec.env_overlays.all()}
        requested_overlays: dict[str, dict] = data["env_overlays"]

        # 构建更新前的审计日志数据
        before_env_overlays = {}
        for env_name in requested_overlays:
            overlay = env_overlays_map.get(env_name)
            if overlay and overlay.override_plan_name:
                override_proc_res = {"plan": overlay.override_plan_name}
            elif overlay and overlay.override_resources:
                override_proc_res = overlay.override_resources
            else:
                override_proc_res = None
            before_env_overlays[env_name] = {"override_proc_res": override_proc_res}

        # 批量更新环境覆盖配置
        overlays_to_update = []
        overlays_to_create = []
        now = timezone.now()
        for env_name, overlay_data in requested_overlays.items():
            if env_overlay := env_overlays_map.get(env_name):
                env_overlay.override_plan_name = overlay_data["override_plan_name"]
                env_overlay.override_resources = overlay_data["override_resources"]
                env_overlay.updated = now
                overlays_to_update.append(env_overlay)
            else:
                overlays_to_create.append(
                    ProcessSpecEnvOverlay(
                        proc_spec=proc_spec,
                        environment_name=env_name,
                        tenant_id=proc_spec.tenant_id,
                        override_plan_name=overlay_data["override_plan_name"],
                        override_resources=overlay_data["override_resources"],
                        updated=now,
                    )
                )
        if overlays_to_create:
            ProcessSpecEnvOverlay.objects.bulk_create(overlays_to_create)
        if overlays_to_update:
            ProcessSpecEnvOverlay.objects.bulk_update(
                overlays_to_update,
                fields=["override_plan_name", "override_resources", "updated"],
            )

        # 构建更新后的审计日志数据
        after_env_overlays = {
            env_name: {
                "override_proc_res": (
                    {"plan": overlay_data["override_plan_name"]}
                    if overlay_data["override_plan_name"]
                    else overlay_data["override_resources"]
                )
            }
            for env_name, overlay_data in requested_overlays.items()
        }

        # 记录审计日志
        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.PROCESS,
            app_code=application.code,
            module_name=module_name,
            attribute=process_name,
            data_before=DataDetail(data={"name": process_name, "env_overlays": before_env_overlays}),
            data_after=DataDetail(data={"name": process_name, "env_overlays": after_env_overlays}),
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    def list_quota_plans(self, request):
        """获取资源配额方案选项列表"""

        result = [
            {
                "name": plan.name,
                "limits": plan.limits,
                "requests": plan.requests,
            }
            for plan in ResQuotaPlan.objects.filter(is_active=True)
        ]

        return Response(result)
