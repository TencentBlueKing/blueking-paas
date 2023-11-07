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
import json
import logging

import yaml
from django.db.transaction import atomic
from django.http.response import HttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.bk_app.cnative.specs.constants import ACCESS_CONTROL_ANNO_KEY, BKPAAS_ADDONS_ANNO_KEY
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppProcess
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.bkapp_model.manager import ModuleProcessSpecManager
from paasng.platform.bkapp_model.manifest import get_manifest
from paasng.platform.bkapp_model.models import ModuleProcessSpec
from paasng.platform.bkapp_model.serializers import (
    GetManifestInputSLZ,
    ModuleDeployHookSLZ,
    ModuleProcessSpecSLZ,
    ModuleProcessSpecsOutputSLZ,
    default_scaling_config,
)
from paasng.platform.bkapp_model.utils import get_image_info
from paasng.platform.engine.constants import AppEnvName, ImagePullPolicy

logger = logging.getLogger(__name__)


# TODO: Remove this API entirely because if become stale
class CNativeAppManifestExtViewset(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """云原生应用扩展信息管理"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.VIEW_BASIC_INFO)]

    def retrieve(self, request, code, module_name, environment):
        """提供应用扩展信息，主要来源为平台扩展功能，如增强服务配置等"""
        engine_app = self.get_engine_app_via_path()
        # 只要绑定即可用于展示，不关心是否已经分配实例
        service_names = [svc.name for svc in mixed_service_mgr.list_binded(engine_app.env.module)]
        manifest_ext = {"metadata": {"annotations": {BKPAAS_ADDONS_ANNO_KEY: json.dumps(service_names)}}}

        try:
            from paasng.security.access_control.models import ApplicationAccessControlSwitch
        except ImportError:
            logger.info('access control only supported in te region, skip...')
        else:
            if ApplicationAccessControlSwitch.objects.is_enabled(self.get_application()):
                manifest_ext["metadata"]["annotations"][ACCESS_CONTROL_ANNO_KEY] = "true"

        return Response(data=manifest_ext)


class BkAppModelManifestsViewset(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """The main viewset for managing the manifests of blueking application model."""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(query_serializer=GetManifestInputSLZ, tags=["云原生应用"])
    def retrieve(self, request, code, module_name):
        """获取当前模块的蓝鲸应用模型数据，支持 JSON、YAML 等不同格式。"""
        slz = GetManifestInputSLZ(data=request.GET)
        slz.is_valid(raise_exception=True)
        module = self.get_module_via_path()

        output_format = slz.validated_data['output_format']
        if output_format == 'yaml':
            manifests = get_manifest(module)
            response = yaml.safe_dump_all(manifests)
            # Use django's response to ignore DRF's renders
            return HttpResponse(response, content_type='application/yaml')
        else:
            return Response(get_manifest(module))

    def replace(self, request, code, module_name):
        """替换当前模块的蓝鲸应用模型数据。"""
        # TODO: Add logics
        return Response({})


class ModuleProcessSpecViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """API for CRUD ModuleProcessSpec"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(response_serializer=ModuleProcessSpecsOutputSLZ)
    def retrieve(self, request, code, module_name):
        """获取当前模块的进程配置"""
        module = self.get_module_via_path()
        proc_specs = ModuleProcessSpec.objects.filter(module=module)
        image_repository, image_credential_name = get_image_info(module)

        images = {proc_spec.image for proc_spec in proc_specs if proc_spec.image is not None}
        # 兼容可以为每个进程单独设置镜像的版本（如 v1alph1 版本时所存储的存量 BkApp 资源）
        allow_multiple_image = len(images - {image_repository}) >= 1

        proc_specs_data = [
            {
                "name": proc_spec.name,
                "image": proc_spec.image or image_repository,
                "image_credential_name": proc_spec.image_credential_name or image_credential_name,
                "command": proc_spec.command or [],
                "args": proc_spec.args or [],
                "port": proc_spec.port,
                "env_overlay": {
                    environment_name.value: {
                        "environment_name": environment_name.value,
                        "plan_name": proc_spec.get_plan_name(environment_name),
                        "target_replicas": proc_spec.get_target_replicas(environment_name),
                        "autoscaling": bool(proc_spec.get_autoscaling(environment_name)),
                        "scaling_config": proc_spec.get_scaling_config(environment_name) or default_scaling_config(),
                    }
                    for environment_name in AppEnvName
                },
            }
            for proc_spec in proc_specs
        ]
        return Response(
            ModuleProcessSpecsOutputSLZ(
                {"metadata": {"allow_multiple_image": allow_multiple_image}, "proc_specs": proc_specs_data}
            ).data
        )

    @swagger_auto_schema(request_body=ModuleProcessSpecSLZ(many=True))
    @atomic
    def batch_upsert(self, request, code, module_name):
        """批量更新模块的进程配置"""
        module = self.get_module_via_path()
        slz = ModuleProcessSpecSLZ(data=request.data, many=True)
        slz.is_valid(raise_exception=True)
        proc_specs = slz.validated_data

        image_repository, image_credential_name = get_image_info(module)
        images = {
            proc_spec.image
            for proc_spec in ModuleProcessSpec.objects.filter(module=module)
            if proc_spec.image is not None
        }
        # 兼容可以为每个进程单独设置镜像的版本（如 v1alph1 版本时所存储的存量 BkApp 资源）
        allow_multiple_image = len(images - {image_repository}) >= 1
        image_credential_names = (
            {}
            if not allow_multiple_image
            else {proc_spec["name"]: proc_spec.get("image_credential_name", None) for proc_spec in proc_specs}
        )

        processes = [
            BkAppProcess(
                name=proc_spec["name"],
                command=proc_spec["command"],
                args=proc_spec["args"],
                targetPort=proc_spec.get("port", None),
                image=proc_spec["image"] if allow_multiple_image else "",
                imagePullPolicy=ImagePullPolicy.IF_NOT_PRESENT,
            )
            for proc_spec in proc_specs
        ]

        mgr = ModuleProcessSpecManager(module)
        # 更新进程配置
        mgr.sync_from_bkapp(processes, image_credential_names)
        # 更新环境覆盖
        for proc_spec in proc_specs:
            if env_overlay := proc_spec.get("env_overlay"):
                mgr.sync_env_overlay(proc_name=proc_spec["name"], env_overlay=env_overlay)
        return self.retrieve(request, code, module_name)


class ModuleDeployHookViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """API for CRUD ModuleDeployHook"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(response_serializer=ModuleDeployHookSLZ)
    def retrieve(self, request, code, module_name, hook_type):
        """查询模块的钩子命令配置"""
        module = self.get_module_via_path()
        hook = module.deploy_hooks.get_by_type(hook_type)
        if not hook:
            return Response(ModuleDeployHookSLZ({"type": hook_type, "enabled": False}).data)
        return Response(ModuleDeployHookSLZ(hook).data)

    @swagger_auto_schema(response_serializer=ModuleDeployHookSLZ, request_body=ModuleDeployHookSLZ)
    def upsert(self, request, code, module_name):
        """更新/创建模块的钩子命令配置"""
        module = self.get_module_via_path()
        slz = ModuleDeployHookSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        if data["enabled"]:
            if proc_command := data.get("proc_command"):
                module.deploy_hooks.enable_hook(type_=data["type"], proc_command=proc_command)
            else:
                module.deploy_hooks.enable_hook(type_=data["type"], command=data["command"], args=data["args"])
        else:
            module.deploy_hooks.disable_hook(type_=data["type"])
        return Response(ModuleDeployHookSLZ(module.deploy_hooks.get_by_type(data["type"])).data)
