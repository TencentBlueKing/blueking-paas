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

import logging

import yaml
from django.db.transaction import atomic
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.bk_app.cnative.specs.models import update_app_resource
from paas_wl.workloads.autoscaling.entities import AutoscalingConfig
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_app_audit_record
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.models import Application
from paasng.platform.bkapp_model import fieldmgr
from paasng.platform.bkapp_model.entities import Monitoring, Process
from paasng.platform.bkapp_model.entities_syncer import sync_processes
from paasng.platform.bkapp_model.fieldmgr.constants import FieldMgrName
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
from paasng.platform.engine.constants import AppEnvName, RuntimeType
from paasng.platform.modules.models import BuildConfig
from paasng.utils.dictx import get_items
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)

# The default scaling config value object when autoscaling config is absent.
default_scaling_config = AutoscalingConfig(min_replicas=1, max_replicas=1, policy="default")


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
            import_manifest(module, manifest, fieldmgr.FieldMgrName.APP_DESC)
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
        build_cfg = BuildConfig.objects.get_or_create_by_module(module)

        image_repository = None
        # 注：只有纯镜像应用需要提供 repository
        if build_cfg.build_method == RuntimeType.CUSTOM_IMAGE:
            # 云原生应用使用 BuildConfig 中记录的值，旧的镜像应用使用 Module 中记录的值
            if module.application.type == ApplicationType.CLOUD_NATIVE:
                image_repository = build_cfg.image_repository
            else:
                image_repository = module.get_source_obj().get_repo_url() or ""

        try:
            observability = module.observability
            proc_metric_map = {m.process: m for m in observability.monitoring_metrics}
        except ObservabilityConfig.DoesNotExist:
            proc_metric_map = {}

        proc_specs = []
        for spec in ModuleProcessSpec.objects.filter(module=module):
            data = {
                "name": spec.name,
                "image": image_repository,
                "proc_command": spec.proc_command,
                "command": spec.command or [],
                "args": spec.args or [],
                "port": spec.port,
                "env_overlay": {
                    environment_name.value: {
                        "plan_name": spec.get_plan_name(environment_name),
                        "target_replicas": spec.get_target_replicas(environment_name),
                        "autoscaling": bool(spec.get_autoscaling(environment_name)),
                        "scaling_config": spec.get_scaling_config(environment_name) or default_scaling_config,
                    }
                    for environment_name in AppEnvName
                },
                "probes": spec.probes or {},
                "services": ([svc.render_port() for svc in spec.services] if spec.services else None),
                "components": spec.components,
            }

            if metric := proc_metric_map.get(spec.name):
                data["monitoring"] = {"metric": metric.dict()}

            proc_specs.append(data)

        resp_data = {"proc_specs": proc_specs}
        return Response(ModuleProcessSpecsOutputSLZ(resp_data).data)

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
                components=proc_spec.get("components", None),
            )
            for proc_spec in proc_specs
        ]

        sync_processes(module, processes, manager=FieldMgrName.WEB_FORM)

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
            fieldmgr.FieldManager(module, fieldmgr.F_HOOKS).set(fieldmgr.FieldMgrName.WEB_FORM)
        else:
            module.deploy_hooks.disable_hook(type_=data["type"])
        return Response(ModuleDeployHookSLZ(module.deploy_hooks.get_by_type(data["type"])).data)


class SvcDiscConfigViewSet(viewsets.GenericViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(responses={200: SvcDiscConfigSLZ()})
    def retrieve(self, request, code):
        """获取当前应用的服务发现配置。

        #### field_manager 字段说明

        本字段表示当前应用模型字段（指“服务发现”）被哪个输入源所管理。应用模型支持多种输入源，
        比如表单编辑器、应用描述文件等。在处理多输入源可能导致的数据冲突时，客户端可依赖
        field_manager 字段来确定处理逻辑。比如在表单编辑器中，发现当前模型字段被应用描述文件（
        app_desc）所管理时，可以选择隐藏“编辑”按钮并加以提示。

        字段可能的值：

        - `null`：表示模型字段不被任何输入源所管理
        - `(object)`：值为当前的输入源（管理者），其中 `name` 的可选值包括：web_form（表单编辑器）、
          app_desc（应用描述文件）
        """
        application = self.get_application()

        svc_disc = get_object_or_404(SvcDiscConfig, application_id=application.id)

        # Set "field_manager" field for rendering
        svc_disc.field_manager = None
        if mgr := self._get_field_manager(application).get():
            svc_disc.field_manager = {"name": mgr.value}

        return Response(SvcDiscConfigSLZ(svc_disc).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(responses={200: SvcDiscConfigSLZ()}, request_body=SvcDiscConfigSLZ)
    def upsert(self, request, code):
        application = self.get_application()
        svc_disc = SvcDiscConfig.objects.filter(application_id=application.id).first()
        data_before = None
        if svc_disc:
            data_before = DataDetail(data=SvcDiscConfigSLZ(svc_disc).data)

        slz = SvcDiscConfigSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        validated_data = slz.validated_data

        svc_disc, created = SvcDiscConfig.objects.update_or_create(
            application_id=application.id,
            defaults={
                "bk_saas": validated_data["bk_saas"],
                "tenant_id": application.tenant_id,
            },
        )
        svc_disc.refresh_from_db()
        self._get_field_manager(application).set(fieldmgr.FieldMgrName.WEB_FORM)

        data = SvcDiscConfigSLZ(svc_disc).data
        add_app_audit_record(
            app_code=code,
            tenant_id=application.tenant_id,
            user=request.user.pk,
            action_id=AppAction.BASIC_DEVELOP,
            operation=OperationEnum.CREATE if created else OperationEnum.MODIFY,
            target=OperationTarget.SERVICE_DISCOVERY,
            data_before=data_before,
            data_after=DataDetail(data=data),
        )
        return Response(data, status=status.HTTP_200_OK)

    def _get_field_manager(self, app: Application) -> fieldmgr.FieldManager:
        # Always use the default module for getting field manager
        return fieldmgr.FieldManager(app.get_default_module(), fieldmgr.F_SVC_DISCOVERY)


class DomainResolutionViewSet(viewsets.GenericViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(responses={200: DomainResolutionSLZ()})
    def retrieve(self, request, code):
        """获取当前应用的域名解析配置。

        - field_manager 字段说明，参考服务发现 .../svc_disc/ API
        """
        application = self.get_application()

        domain_res = get_object_or_404(DomainResolution, application_id=application.id)

        # Set "field_manager" field for rendering
        domain_res.field_manager = None
        if mgr := self._get_field_manager(application).get():
            domain_res.field_manager = {"name": mgr.value}

        return Response(DomainResolutionSLZ(domain_res).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(responses={200: DomainResolutionSLZ()}, request_body=DomainResolutionSLZ)
    def upsert(self, request, code):
        application = self.get_application()
        domain_resolution = DomainResolution.objects.filter(application_id=application.id).first()
        data_before = None
        if domain_resolution:
            data_before = DataDetail(data=DomainResolutionSLZ(domain_resolution).data)

        slz = DomainResolutionSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        validated_data = slz.validated_data

        defaults = {"tenant_id": application.tenant_id}
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
        self._get_field_manager(application).set(fieldmgr.FieldMgrName.WEB_FORM)

        data = DomainResolutionSLZ(domain_resolution).data
        add_app_audit_record(
            app_code=code,
            tenant_id=application.tenant_id,
            user=request.user.pk,
            action_id=AppAction.BASIC_DEVELOP,
            operation=OperationEnum.CREATE if created else OperationEnum.MODIFY,
            target=OperationTarget.DOMAIN_RESOLUTION,
            data_before=data_before,
            data_after=DataDetail(data=data),
        )
        return Response(data, status=status.HTTP_200_OK)

    def _get_field_manager(self, app: Application) -> fieldmgr.FieldManager:
        # Always use the default module for getting field manager
        return fieldmgr.FieldManager(app.get_default_module(), fieldmgr.F_DOMAIN_RESOLUTION)
