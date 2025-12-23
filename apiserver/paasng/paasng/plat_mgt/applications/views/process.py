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
from paasng.platform.bkapp_model.models import ModuleProcessSpec, ProcessSpecEnvOverlay
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

        proc_specs = list(ModuleProcessSpec.objects.filter(module=module).prefetch_related("env_overlays"))

        # 构建进程列表
        processes = []
        for spec in proc_specs:
            # 构建环境覆盖配置
            overlays_map = {o.environment_name: o for o in spec.env_overlays.all()}
            env_overlays = {}

            for env_name in AppEnvName.get_values():
                overlay = overlays_map.get(env_name)

                if overlay and overlay.override_proc_res:
                    # 使用自定义资源配置
                    env_overlays[env_name] = {"plan_name": None, "resources": overlay.override_proc_res}
                else:
                    # 使用资源配额方案
                    plan_name = (
                        overlay.override_plan_name
                        if overlay and overlay.override_plan_name
                        else spec.get_plan_name(env_name)
                    )
                    env_overlays[env_name] = {"plan_name": plan_name, "resources": None}

            processes.append({"name": spec.name, "env_overlays": env_overlays})

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
        if module.source_origin not in [
            SourceOrigin.CNATIVE_IMAGE.value,
            SourceOrigin.S_MART.value,
            SourceOrigin.AI_AGENT.value,
        ]:
            return Response(
                {"detail": _("该模块的源码来源不支持修改进程资源配置")},
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
        requested_overlays = data["env_overlays"]

        # 记录更新前状态
        before_env_overlays = {}
        for env_name in requested_overlays:
            overlay = env_overlays_map.get(env_name)
            if overlay:
                before_env_overlays[env_name] = {
                    "override_plan_name": overlay.override_plan_name,
                    "override_resources": overlay.override_proc_res,
                }
            else:
                before_env_overlays[env_name] = {
                    "override_plan_name": None,
                    "override_resources": None,
                }

        # 批量更新
        overlays_to_update = []
        overlays_to_create = []

        for env_name, overlay_data in requested_overlays.items():
            env_overlay = env_overlays_map.get(env_name)

            if not env_overlay:
                # 创建新的环境覆盖
                env_overlay = ProcessSpecEnvOverlay(
                    proc_spec=proc_spec, environment_name=env_name, tenant_id=proc_spec.tenant_id
                )
                overlays_to_create.append(env_overlay)

            # 更新配置
            if overlay_data["resources"] is not None:
                # 使用自定义资源配置
                env_overlay.override_proc_res = overlay_data["resources"]
                env_overlay.override_plan_name = None
            else:
                # 清空自定义资源配置
                env_overlay.override_plan_name = overlay_data["plan_name"]
                env_overlay.override_proc_res = None

            env_overlay.updated = timezone.now()
            if env_overlay.pk:
                overlays_to_update.append(env_overlay)

        # 批量创建和更新
        if overlays_to_create:
            ProcessSpecEnvOverlay.objects.bulk_create(overlays_to_create)

        if overlays_to_update:
            ProcessSpecEnvOverlay.objects.bulk_update(
                overlays_to_update,
                fields=["override_proc_res", "override_plan_name", "updated"],
            )

        # 记录审计日志
        add_plat_mgt_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.PROCESS,
            app_code=application.code,
            module_name=module_name,
            attribute=process_name,
            data_before=DataDetail(data={"name": process_name, "env_overlays": before_env_overlays}),
            data_after=DataDetail(data={"name": process_name, "env_overlays": requested_overlays}),
        )

        return Response(status=status.HTTP_204_NO_CONTENT)
