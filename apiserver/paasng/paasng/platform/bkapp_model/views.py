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

import json
import logging

import yaml
from django.db.transaction import atomic
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.bk_app.cnative.specs.constants import ACCESS_CONTROL_ANNO_KEY, BKPAAS_ADDONS_ANNO_KEY
from paas_wl.bk_app.cnative.specs.models import update_app_resource
from paas_wl.workloads.autoscaling.entities import AutoscalingConfig
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.audit.constants import DataType, OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_app_audit_record
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.bkapp_model.entities import Monitoring, Process
from paasng.platform.bkapp_model.entities_syncer import sync_processes
from paasng.platform.bkapp_model.importer import import_manifest
from paasng.platform.bkapp_model.manifest import get_manifest
from paasng.platform.bkapp_model.models import (
    DomainResolution,
    ModuleProcessSpec,
    ObservabilityConfig,
    ProcessSpecEnvOverlay,
    SvcDiscConfig,
)
from paasng.platform.bkapp_model.serializers import (
    BkAppModelSLZ,
    DomainResolutionSLZ,
    GetManifestInputSLZ,
    ModuleDeployHookSLZ,
    ModuleProcessSpecsInputSLZ,
    ModuleProcessSpecsOutputSLZ,
    SvcDiscConfigSLZ,
)
from paasng.platform.bkapp_model.utils import get_image_info
from paasng.platform.engine.constants import AppEnvName
from paasng.utils.dictx import get_items
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)

# The default scaling config value object when autoscaling config is absent.
default_scaling_config = AutoscalingConfig(min_replicas=1, max_replicas=1, policy="default")


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
            logger.info("access control only supported in te region, skip...")
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

        output_format = slz.validated_data["output_format"]
        if output_format == "yaml":
            manifests = get_manifest(module)
            response = yaml.safe_dump_all(manifests)
            # Use django's response to ignore DRF's renders
            return HttpResponse(response, content_type="application/yaml")
        else:
            return Response(get_manifest(module))

    @swagger_auto_schema(request_body=BkAppModelSLZ)
    def replace(self, request, code, module_name):
        """通过 manifest 更新应用模型资源"""
        application = self.get_application()
        module = self.get_module_via_path()

        serializer = BkAppModelSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)

        manifest = serializer.validated_data.get("manifest")

        update_app_resource(application, module, manifest)
        try:
            import_manifest(module, manifest)
        except Exception as e:
            raise error_codes.IMPORT_MANIFEST_FAILED.f(str(e))

        return Response(data=get_manifest(module), status=status.HTTP_200_OK)


class ModuleProcessSpecViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """API for CRUD ModuleProcessSpec"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(response_serializer=ModuleProcessSpecsOutputSLZ)
    def retrieve(self, request, code, module_name):
        """获取当前模块的进程配置"""
        module = self.get_module_via_path()
        proc_specs = ModuleProcessSpec.objects.filter(module=module)
        image_repository, image_credential_name = get_image_info(module)

        try:
            observability = module.observability
            proc_metric_map = {m.process: m for m in observability.monitoring_metrics}
        except ObservabilityConfig.DoesNotExist:
            proc_metric_map = {}

        proc_specs_data = []
        for proc_spec in proc_specs:
            data = {
                "name": proc_spec.name,
                "image": image_repository,
                "image_credential_name": image_credential_name,
                "command": proc_spec.command or [],
                "args": proc_spec.args or [],
                "port": proc_spec.port,
                "env_overlay": {
                    environment_name.value: {
                        "plan_name": proc_spec.get_plan_name(environment_name),
                        "target_replicas": proc_spec.get_target_replicas(environment_name),
                        "autoscaling": bool(proc_spec.get_autoscaling(environment_name)),
                        "scaling_config": proc_spec.get_scaling_config(environment_name) or default_scaling_config,
                    }
                    for environment_name in AppEnvName
                },
                "probes": proc_spec.probes or {},
                "services": proc_spec.services,
            }

            if metric := proc_metric_map.get(proc_spec.name):
                data["monitoring"] = {"metric": metric.dict()}

            proc_specs_data.append(data)
        return Response(
            ModuleProcessSpecsOutputSLZ(
                {"metadata": {"allow_multiple_image": False}, "proc_specs": proc_specs_data}
            ).data
        )

    @swagger_auto_schema(request_body=ModuleProcessSpecsInputSLZ)
    @atomic
    def batch_upsert(self, request, code, module_name):
        """批量更新模块的进程配置"""
        module = self.get_module_via_path()
        slz = ModuleProcessSpecsInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        proc_specs = slz.validated_data["proc_specs"]
        processes = [
            Process(
                name=proc_spec["name"],
                command=proc_spec["command"],
                args=proc_spec["args"],
                target_port=proc_spec.get("port", None),
                probes=proc_spec.get("probes", None),
                services=proc_spec.get("services", None),
            )
            for proc_spec in proc_specs
        ]

        sync_processes(module, processes)

        # 更新环境覆盖&更新可观测功能配置
        metrics = []
        for proc_spec in proc_specs:
            if env_overlay := proc_spec.get("env_overlay"):
                for env_name, proc_env_overlay in env_overlay.items():
                    ProcessSpecEnvOverlay.objects.save_by_module(
                        module, proc_spec["name"], env_name, **proc_env_overlay
                    )
            if metric := get_items(proc_spec, "monitoring.metric"):
                metrics.append({"process": proc_spec["name"], **metric})

        monitoring = Monitoring(metrics=metrics) if metrics else None
        ObservabilityConfig.objects.upsert_by_module(module, monitoring)

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


class SvcDiscConfigViewSet(viewsets.GenericViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(responses={200: SvcDiscConfigSLZ()})
    def retrieve(self, request, code):
        application = self.get_application()

        svc_disc = get_object_or_404(SvcDiscConfig, application_id=application.id)
        return Response(SvcDiscConfigSLZ(svc_disc).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(responses={200: SvcDiscConfigSLZ()}, request_body=SvcDiscConfigSLZ)
    def upsert(self, request, code):
        application = self.get_application()
        svc_disc = SvcDiscConfig.objects.filter(application_id=application.id).first()
        data_before = None
        if svc_disc:
            data_before = DataDetail(type=DataType.RAW_DATA, data=SvcDiscConfigSLZ(svc_disc).data)

        slz = SvcDiscConfigSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        validated_data = slz.validated_data

        svc_disc, created = SvcDiscConfig.objects.update_or_create(
            application_id=application.id,
            defaults={
                "bk_saas": validated_data["bk_saas"],
            },
        )
        svc_disc.refresh_from_db()
        data = SvcDiscConfigSLZ(svc_disc).data
        add_app_audit_record(
            app_code=code,
            user=request.user.pk,
            action_id=AppAction.BASIC_DEVELOP,
            operation=OperationEnum.CREATE if created else OperationEnum.MODIFY,
            target=OperationTarget.SERVICE_DISCOVERY,
            data_before=data_before,
            data_after=DataDetail(type=DataType.RAW_DATA, data=data),
        )
        return Response(data, status=status.HTTP_200_OK)


class DomainResolutionViewSet(viewsets.GenericViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(responses={200: DomainResolutionSLZ()})
    def retrieve(self, request, code):
        application = self.get_application()

        domain_res = get_object_or_404(DomainResolution, application_id=application.id)
        return Response(DomainResolutionSLZ(domain_res).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(responses={200: DomainResolutionSLZ()}, request_body=DomainResolutionSLZ)
    def upsert(self, request, code):
        application = self.get_application()
        domain_resolution = DomainResolution.objects.filter(application_id=application.id).first()
        data_before = None
        if domain_resolution:
            data_before = DataDetail(type=DataType.RAW_DATA, data=DomainResolutionSLZ(domain_resolution).data)

        slz = DomainResolutionSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        validated_data = slz.validated_data

        defaults = {}
        nameservers = validated_data.get("nameservers")
        if nameservers is not None:
            defaults["nameservers"] = nameservers
        host_aliases = validated_data.get("host_aliases")
        if host_aliases is not None:
            defaults["host_aliases"] = host_aliases

        domain_resolution, created = DomainResolution.objects.update_or_create(
            application=application, defaults=defaults
        )

        domain_resolution.refresh_from_db()

        data = DomainResolutionSLZ(domain_resolution).data
        add_app_audit_record(
            app_code=code,
            user=request.user.pk,
            action_id=AppAction.BASIC_DEVELOP,
            operation=OperationEnum.CREATE if created else OperationEnum.MODIFY,
            target=OperationTarget.DOMAIN_RESOLUTION,
            data_before=data_before,
            data_after=DataDetail(type=DataType.RAW_DATA, data=data),
        )
        return Response(data, status=status.HTTP_200_OK)
