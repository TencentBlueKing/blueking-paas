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
from typing import Optional, Tuple

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
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.bkapp_model.manager import ModuleProcessSpecManager
from paasng.platform.bkapp_model.manifest import get_manifest
from paasng.platform.bkapp_model.models import ModuleProcessSpec
from paasng.platform.bkapp_model.serializers import GetManifestInputSLZ, ModuleProcessSpecSLZ
from paasng.platform.engine.configurations.image import generate_image_repository
from paasng.platform.engine.constants import AppEnvName, RuntimeType
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.helpers import ModuleRuntimeManager
from paasng.platform.modules.models import BuildConfig, Module

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


class ModuleProcessSpecViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """API for CRUD ModuleProcessSpec"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(response_serializer=ModuleProcessSpecSLZ(many=True))
    def retrieve(self, request, code, module_name):
        """获取当前模块的进程配置"""
        module = self.get_module_via_path()
        proc_specs = ModuleProcessSpec.objects.filter(module=module)
        image_repository, image_credential_name = self.get_image_info(module)

        images = {proc_spec.image for proc_spec in proc_specs if proc_spec.image is not None}
        # 兼容 v1alpha1
        allow_set_image = len(images - {image_repository}) >= 1

        data = [
            {
                "name": proc_spec.name,
                "image": proc_spec.image or image_repository,
                "image_credential_name": proc_spec.image_credential_name or image_credential_name,
                "command": proc_spec.command,
                "args": proc_spec.args,
                "port": proc_spec.port,
                "env_overlay": {
                    env_name.value: {
                        "environment_name": env_name.value,
                        "plan_name": proc_spec.get_plan_name(environment_name=env_name),
                        "target_replicas": proc_spec.get_target_replicas(environment_name=env_name),
                        "autoscaling": proc_spec.get_autoscaling(environment_name=env_name),
                        "scaling_config": proc_spec.get_scaling_config(environment_name=env_name),
                    }
                    for env_name in AppEnvName
                },
                "metadata": {
                    "allow_set_image": allow_set_image,
                },
            }
            for proc_spec in proc_specs
        ]
        return Response(ModuleProcessSpecSLZ(data, many=True).data)

    @swagger_auto_schema(request_body=ModuleProcessSpecSLZ(many=True))
    @atomic
    def batch_upsert(self, request, code, module_name):
        """批量更新模块的进程配置"""
        module = self.get_module_via_path()
        slz = ModuleProcessSpecSLZ(data=request.data, many=True)
        slz.is_valid(raise_exception=True)
        proc_specs = slz.validated_data

        images = set(ModuleProcessSpec.objects.filter(module=module).values_list("image", flat=True))
        # 兼容 v1alpha1
        allow_set_image = len(images) >= 2

        processes = [
            BkAppProcess(
                name=proc_spec["name"],
                command=proc_spec["command"],
                args=proc_spec["args"],
                targetPort=proc_spec["port"],
                image=proc_spec["image"] if allow_set_image else None,
            )
            for proc_spec in proc_specs
        ]

        mgr = ModuleProcessSpecManager(module)
        # 更新进程配置
        mgr.sync_form_bkapp(processes)
        # 更新环境覆盖
        mgr.sync_env_overlay(proc_specs)
        return self.retrieve(request, code, module_name)

    @staticmethod
    def get_image_info(module: Module) -> Tuple[str, Optional[str]]:
        """获取模块的镜像仓库和访问凭证名"""
        build_cfg = BuildConfig.objects.get_or_create_by_module(module)
        if build_cfg.build_method == RuntimeType.CUSTOM_IMAGE:
            if module.application.type == ApplicationType.CLOUD_NATIVE:
                return build_cfg.image_repository, build_cfg.image_credential_name
            return module.get_source_obj().get_repo_url() or "", None
        elif build_cfg.build_method == RuntimeType.DOCKERFILE:
            return generate_image_repository(module), None
        elif module.get_source_origin() == SourceOrigin.S_MART:
            raise ValueError
        mgr = ModuleRuntimeManager(module)
        if mgr.is_cnb_runtime:
            return generate_image_repository(module), None
        raise ValueError
