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
from paasng.plat_mgt.applications.serializers import ModuleProcessSpecInputSLZ, ModuleProcessSpecOutputSLZ
from paasng.platform.applications.models import Application
from paasng.platform.bkapp_model.constants import CPUResourceQuantity, MemoryResourceQuantity
from paasng.platform.bkapp_model.models import ModuleProcessSpec, ProcessSpecEnvOverlay
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.modules.constants import SourceOrigin


class ApplicationProcessViewSet(viewsets.GenericViewSet):
    """平台管理 - 应用进程 API"""

    queryset = Application.objects.all()
    permission_classes = [IsAuthenticated, plat_mgt_perm_class(PlatMgtAction.ALL)]

    @swagger_auto_schema(
        tags=["plat_mgt.process"],
        operation_description="获取应用的进程资源限制",
        responses={status.HTTP_200_OK: ModuleProcessSpecOutputSLZ(many=True)},
    )
    def list_resource(self, request, app_code):
        """获取应用的进程资源限制"""
        application = get_object_or_404(self.get_queryset(), code=app_code)

        proc_specs = list(
            ModuleProcessSpec.objects.filter(module__application=application)
            .select_related("module")
            .prefetch_related("env_overlays")
        )

        # 构建按模块分组的结果
        modules_map = {}
        for spec in proc_specs:
            module_name = spec.module.name
            source_origin = spec.module.source_origin
            if module_name not in modules_map:
                modules_map[module_name] = {
                    "module_name": module_name,
                    "source_origin": source_origin,
                    "processes": [],
                }

            # 构建环境覆盖配置
            overlays_map = {o.environment_name: o for o in spec.env_overlays.all()}
            env_overlays = {}

            for env_name in AppEnvName.get_values():
                overlay = overlays_map.get(env_name)

                if overlay and overlay.override_proc_res:
                    env_overlays[env_name] = {"plan_name": None, "resources": overlay.override_proc_res}
                else:
                    env_overlays[env_name] = {
                        "plan_name": spec.get_plan_name(env_name),
                        "resources": None,
                    }

            modules_map[module_name]["processes"].append(
                {
                    "name": spec.name,
                    "env_overlays": env_overlays,
                }
            )

        return Response(ModuleProcessSpecOutputSLZ(list(modules_map.values()), many=True).data)

    @swagger_auto_schema(
        tags=["plat_mgt.process"],
        operation_description="更新应用的进程资源限制",
        request_body=ModuleProcessSpecInputSLZ(),
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def update_resource(self, request, app_code):
        """更新应用的进程资源限制"""
        application = get_object_or_404(self.get_queryset(), code=app_code)
        slz = ModuleProcessSpecInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        module_name = data["module_name"]
        processes_data = data["processes"]
        process_names = [p["name"] for p in processes_data]

        # 校验 module 的 source_origin 是否可以修改
        module = get_object_or_404(application.modules, name=module_name)
        if module.source_origin not in [
            SourceOrigin.CNATIVE_IMAGE.value,
            SourceOrigin.S_MART.value,
            SourceOrigin.AI_AGENT.value,
        ]:
            return Response(
                {"detail": _("该模块的源码来源不支持修改进程资源配置")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 批量查询所有相关的进程规格和环境覆盖
        proc_specs = ModuleProcessSpec.objects.filter(
            module__application=application, module__name=module_name, name__in=process_names
        ).prefetch_related("env_overlays")

        # 构建进程规格映射
        proc_spec_map = {spec.name: spec for spec in proc_specs}

        # 验证所有进程是否存在
        missing_processes = set(process_names) - set(proc_spec_map.keys())
        if missing_processes:
            return Response(
                {"detail": f"进程不存在: {', '.join(missing_processes)}"}, status=status.HTTP_404_NOT_FOUND
            )

        # 收集需要批量更新的对象
        overlays_to_update = []
        overlays_to_create = []
        all_before_processes = []
        all_after_processes = []

        for process_data in processes_data:
            process_name = process_data["name"]
            requested_overlays = process_data["env_overlays"]
            proc_spec = proc_spec_map[process_name]

            # 构建环境覆盖映射
            env_overlays_map = {o.environment_name: o for o in proc_spec.env_overlays.all()}
            before_env_overlays = {}

            for env_name, overlay_data in requested_overlays.items():
                env_overlay = env_overlays_map.get(env_name)

                # 记录更新前状态
                if env_overlay:
                    before_env_overlays[env_name] = {
                        "plan_name": env_overlay.plan_name or proc_spec.plan_name,
                        "resources": env_overlay.override_proc_res,
                    }
                else:
                    # 创建新的环境覆盖
                    env_overlay = ProcessSpecEnvOverlay(
                        proc_spec=proc_spec, environment_name=env_name, tenant_id=proc_spec.tenant_id
                    )
                    before_env_overlays[env_name] = {"plan_name": proc_spec.plan_name, "resources": None}
                    overlays_to_create.append(env_overlay)
                    env_overlays_map[env_name] = env_overlay

                # 更新配置
                if overlay_data.get("resources") is not None:
                    # 使用自定义资源配置
                    env_overlay.override_proc_res = overlay_data["resources"]
                    env_overlay.plan_name = None
                else:
                    # 使用预设方案
                    env_overlay.plan_name = overlay_data.get("plan_name")
                    env_overlay.override_proc_res = None

                env_overlay.updated = timezone.now()
                if env_overlay.pk:
                    overlays_to_update.append(env_overlay)

            all_before_processes.append({"name": process_name, "env_overlays": before_env_overlays})
            all_after_processes.append({"name": process_name, "env_overlays": requested_overlays})

        # 批量创建和更新
        if overlays_to_create:
            ProcessSpecEnvOverlay.objects.bulk_create(overlays_to_create)

        if overlays_to_update:
            ProcessSpecEnvOverlay.objects.bulk_update(
                overlays_to_update, fields=["plan_name", "override_proc_res", "updated"]
            )

        # 记录审计日志
        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.PROCESS,
            app_code=application.code,
            module_name=module_name,
            attribute=", ".join(process_names),
            data_before=DataDetail(
                data=ModuleProcessSpecOutputSLZ(
                    {
                        "module_name": module_name,
                        "source_origin": module.source_origin,
                        "processes": all_before_processes,
                    },
                ).data
            ),
            data_after=DataDetail(
                data=ModuleProcessSpecOutputSLZ(
                    {
                        "module_name": module_name,
                        "source_origin": module.source_origin,
                        "processes": all_after_processes,
                    },
                ).data
            ),
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_custom_resources(self, request):
        """获取应用的自定义资源配置"""

        cpu_resource_quantity = [
            {"value": value, "label": label} for value, label in CPUResourceQuantity.get_choices()
        ]
        memory_resource_quantity = [
            {"value": value, "label": label} for value, label in MemoryResourceQuantity.get_choices()
        ]

        result = {
            "cpu_resource_quantity": cpu_resource_quantity,
            "memory_resource_quantity": memory_resource_quantity,
        }

        return Response(result, status=status.HTTP_200_OK)
