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
from typing import Any, Dict, List

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.accessories.servicehub import serializers as slzs
from paasng.accessories.servicehub.exceptions import (
    BindServiceNoPlansError,
    ReferencedAttachmentNotFound,
    ServiceObjNotFound,
    SharedAttachmentAlreadyExists,
    SvcInstanceNotFound,
)
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.models import ServiceSetGroupByName
from paasng.accessories.servicehub.remote.manager import (
    RemoteServiceInstanceMgr,
    RemoteServiceMgr,
    get_app_by_instance_name,
)
from paasng.accessories.servicehub.remote.store import get_remote_store
from paasng.accessories.servicehub.services import ServiceObj, ServicePlansHelper, ServiceSpecificationHelper
from paasng.accessories.servicehub.sharing import ServiceSharingManager, SharingReferencesManager
from paasng.accessories.services.models import ServiceCategory
from paasng.core.region.models import get_all_regions
from paasng.infras.accounts.permissions.application import app_action_required, application_perm_class
from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.audit.constants import DataType, OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_app_audit_record
from paasng.misc.metrics import SERVICE_BIND_COUNTER
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.models import Application, UserApplicationFilter
from paasng.platform.applications.protections import ProtectedRes, raise_if_protected, res_must_not_be_protected_perm
from paasng.platform.applications.serializers import ApplicationMembersInfoSLZ
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.engine.phases_steps.display_blocks import ServicesInfo
from paasng.platform.modules.manager import ModuleCleaner
from paasng.platform.modules.models import Module
from paasng.platform.modules.serializers import MinimalModuleSLZ
from paasng.platform.templates.constants import TemplateType
from paasng.platform.templates.models import Template
from paasng.utils.api_docs import openapi_empty_response
from paasng.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


class ModuleServiceAttachmentsViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """蓝鲸应用(模块)增强服务附件相关视图"""

    permission_classes = [
        IsAuthenticated,
        application_perm_class(AppAction.BASIC_DEVELOP),
        res_must_not_be_protected_perm(ProtectedRes.SERVICES_MODIFICATIONS),
    ]

    @swagger_auto_schema(response_serializer=slzs.EnvServiceAttachmentSLZ(many=True))
    def list(self, request, code, module_name, environment):
        """获取增强服务附件列表"""

        env = self.get_env_via_path()
        engine_app = env.get_engine_app()
        provisioned_rels = list(mixed_service_mgr.list_provisioned_rels(engine_app))
        unprovisioned_rels = list(mixed_service_mgr.list_unprovisioned_rels(engine_app))
        return Response(data=slzs.EnvServiceAttachmentSLZ(provisioned_rels + unprovisioned_rels, many=True).data)

    @swagger_auto_schema(response_serializer=slzs.ModuleServiceInfoSLZ)
    def retrieve_info(self, request, code, module_name):
        """获取指定模块所有环境的增强服务使用信息"""
        services_info = {}
        for env in self.get_module_via_path().get_envs():
            services_info[env.environment] = ServicesInfo.get_detail(env.engine_app)["services_info"]
        return Response(data=slzs.ModuleServiceInfoSLZ(services_info).data)


class ModuleServicesViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """与蓝鲸应用模块相关的增强服务接口"""

    @staticmethod
    def get_service(service_id, application):
        return mixed_service_mgr.get_or_404(service_id, region=application.region)

    def _get_application_by_code(self, application_code):
        application = get_object_or_404(Application, code=application_code)
        # NOTE: 必须检查是否具有操作 app 的权限
        self.check_object_permissions(self.request, application)
        return application

    @transaction.atomic
    @swagger_auto_schema(request_body=slzs.CreateAttachmentSLZ, response_serializer=slzs.ServiceAttachmentSLZ)
    @app_action_required(AppAction.BASIC_DEVELOP)
    def bind(self, request):
        """创建蓝鲸应用与增强服务的绑定关系"""
        serializer = slzs.CreateAttachmentSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.data
        specs = data["specs"]
        application = self._get_application_by_code(data["code"])
        service_obj = self.get_service(data["service_id"], application)
        module = application.get_module(data.get("module_name", None))

        try:
            rel_pk = mixed_service_mgr.bind_service(service_obj, module, specs)
        except BindServiceNoPlansError as e:
            logger.warning(
                "No plans can be found for service %s, specs: %s, environment: %s.", service_obj.uuid, specs, str(e)
            )
            raise error_codes.CANNOT_BIND_SERVICE.f(_("当前配置规格不可用"))
        except Exception:
            logger.exception("bind service %s to module %s error.", service_obj.uuid, module.name)
            raise error_codes.CANNOT_BIND_SERVICE.f("Unknown error")

        for env in module.envs.all():
            for rel in mixed_service_mgr.list_unprovisioned_rels(env.engine_app, service_obj):
                plan = rel.get_plan()
                if plan.is_eager:
                    rel.provision()

        SERVICE_BIND_COUNTER.labels(service=service_obj.name, region=application.region).inc()
        serializer = slzs.ServiceAttachmentSLZ(
            {
                "id": rel_pk,
                "application": application,
                "service": service_obj.uuid,
                "module_name": module.name,
            }
        )

        add_app_audit_record(
            app_code=application.code,
            user=request.user.pk,
            action_id=AppAction.BASIC_DEVELOP,
            operation=OperationEnum.ENABLE,
            target=OperationTarget.ADD_ON,
            attribute=service_obj.name,
            module_name=module.name,
            data_after=DataDetail(type=DataType.RAW_DATA, data=service_obj.config),
        )
        return Response(serializer.data)

    @app_action_required(AppAction.BASIC_DEVELOP)
    def retrieve(self, request, code, module_name, service_id):
        """查看应用模块与增强服务的绑定关系详情"""
        application = self.get_application()
        module = self.get_module_via_path()
        service = self.get_service(service_id, application)

        # 如果模块与增强服务之间没有绑定关系，直接返回 404 状态码
        if not mixed_service_mgr.module_is_bound_with(service, module):
            raise Http404

        results = []
        for env in module.envs.all():
            for rel in mixed_service_mgr.list_provisioned_rels(env.engine_app, service=service):
                instance = rel.get_instance()
                plan = rel.get_plan()
                results.append(
                    {
                        "service_instance": instance,
                        "environment": env.environment,
                        "environment_name": AppEnvName.get_choice_label(env.environment),
                        "service_specs": plan.specifications,
                        "usage": "{}",
                    }
                )
        serializer = slzs.ServiceInstanceInfoSLZ(results, many=True)
        return Response({"count": len(results), "results": serializer.data})

    @app_action_required(AppAction.BASIC_DEVELOP)
    def retrieve_unbound_instances(self, request, code, module_name, service_id):
        """查看应用模块与增强服务已解绑实例详情"""
        application = self.get_application()
        module = self.get_module_via_path()
        service = self.get_service(service_id, application)

        results = []
        for env in module.envs.all():
            for rel in mixed_service_mgr.list_unbound_instance_rels(env.engine_app, service=service):
                try:
                    instance = rel.get_instance()
                except SvcInstanceNotFound:
                    # 如果已经回收了，获取不到 instance，跳过
                    continue
                plan = rel.get_plan()
                results.append(
                    {
                        "service_instance": instance,
                        "environment": env.environment,
                        "environment_name": AppEnvName.get_choice_label(env.environment),
                        "service_specs": plan.specifications,
                        "usage": "{}",
                    }
                )
        serializer = slzs.ServiceInstanceInfoSLZ(results, many=True)
        return Response({"count": len(results), "results": serializer.data})

    @app_action_required(AppAction.BASIC_DEVELOP)
    def retrieve_specs(self, request, code, module_name, service_id):
        """获取应用已绑定的服务规格"""
        application = self.get_application()
        module = self.get_module_via_path()
        service = self.get_service(service_id, application)

        # 如果模块与增强服务之间没有绑定关系，直接返回 404 状态码
        if not mixed_service_mgr.module_is_bound_with(service, module):
            raise Http404

        specs = {}
        for env in module.envs.all():
            for rel in mixed_service_mgr.list_all_rels(env.engine_app, service_id=service_id):
                plan = rel.get_plan()
                specs = plan.specifications
                break  # 现阶段所有环境的服务规格一致，因此只需要拿一个

        results = []
        # 拼接描述,免得前端请求多个接口
        for definition in service.specifications:
            result = definition.as_dict()
            result["value"] = specs.get(definition.name)
            results.append(result)

        slz = slzs.ServicePlanSpecificationSLZ(results, many=True)
        return Response({"results": slz.data})

    @app_action_required(AppAction.MANAGE_ADDONS_SERVICES)
    @transaction.atomic
    def unbind(self, request, code, module_name, service_id):
        """删除一个服务绑定关系"""
        application = self._get_application_by_code(code)
        module = application.get_module(module_name)
        service = self.get_service(service_id, application)

        # Check if application was protected
        raise_if_protected(application, ProtectedRes.SERVICES_MODIFICATIONS)

        try:
            module_attachment = mixed_service_mgr.get_module_rel(module_id=module.id, service_id=service_id)
        except Exception as e:
            logger.exception("Unable to get module relationship")
            raise error_codes.CANNOT_DESTROY_SERVICE.f(f"{e}")

        cleaner = ModuleCleaner(module=module)
        try:
            cleaner.delete_services(service_id=service_id)
        except Exception as e:
            logger.exception("Unable to unbind service: %s", service_id)
            raise error_codes.CANNOT_DESTROY_SERVICE.f(f"{e}")

        module_attachment.delete()

        add_app_audit_record(
            app_code=code,
            user=request.user.pk,
            action_id=AppAction.MANAGE_ADDONS_SERVICES,
            operation=OperationEnum.DISABLE,
            target=OperationTarget.ADD_ON,
            attribute=service.name,
            module_name=module_name,
            data_before=DataDetail(type=DataType.RAW_DATA, data=service.config if service else None),
        )
        return Response(status=status.HTTP_200_OK)

    @app_action_required(AppAction.BASIC_DEVELOP)
    def list_provisioned_env_keys(self, request, code, module_name):
        """获取已经生效的增强服务环境变量 KEY"""
        module = self.get_module_via_path()

        # env_key_dict 内容示例： {"svc_name": ["key1", "key2"]}
        env_key_dict: Dict[str, List[str]] = {}
        for env in module.get_envs():
            env_key_dict = {
                **env_key_dict,
                **ServiceSharingManager(env.module).get_enabled_env_keys(env),
                **mixed_service_mgr.get_enabled_env_keys(env.engine_app),
            }
        return Response(data=env_key_dict)


class ServiceViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """增强服务相关视图(与应用无关的)"""

    serializer_class = slzs.ServiceSLZ
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @property
    def paginator(self):
        if not hasattr(self, "_paginator"):
            self._paginator = LimitOffsetPagination()
            self._paginator.default_limit = 5
        return self._paginator

    def retrieve(self, request, service_id):
        """获取服务详细信息"""
        service = mixed_service_mgr.get_without_region(uuid=service_id)
        serializer = self.serializer_class(service)
        return Response({"result": serializer.data})

    def list_by_template(self, request, region, template):
        """根据初始模板获取相关增强服务"""
        tmpl = Template.objects.get(name=template, type=TemplateType.NORMAL)
        services = {}
        for name, info in tmpl.preset_services_config.items():
            try:
                service = mixed_service_mgr.find_by_name(name, region)
            except ServiceObjNotFound:
                logger.exception("Failed to get enhanced service <%s> preset in template <%s>", name, template)
                continue

            helper = ServiceSpecificationHelper.from_service_public_specifications(service)
            slz = slzs.ServiceWithSpecsSLZ(
                {
                    "uuid": service.uuid,
                    "name": service.name,
                    "display_name": service.display_name,
                    "description": service.description,
                    "category": service.category,
                    "specs": helper.format_given_specs(info.get("specs", {})),
                }
            )
            services[service.name] = slz.data

        return Response({"result": services})

    def list_by_region(self, request, region):
        """根据region获取所有增强服务"""
        results = []
        for category in ServiceCategory.objects.order_by("sort_priority").all():
            services = []
            for service in mixed_service_mgr.list_by_category(region=region, category_id=category.id):
                if not service.is_visible:
                    continue

                services.append(service)

            if services:
                results.append({"category": category, "services": services})
        serializer = slzs.ServiceCategoryByRegionSLZ(results, many=True)
        return Response({"count": len(results), "results": serializer.data})

    @swagger_auto_schema(query_serializer=slzs.ServiceAttachmentQuerySLZ)
    def list_related_apps(self, request, service_id):
        """获取服务绑定的所有应用"""
        serializer = slzs.ServiceAttachmentQuerySLZ(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        param = serializer.data
        application_ids = list(Application.objects.filter_by_user(request.user).values_list("id", flat=True))

        service = mixed_service_mgr.get_without_region(uuid=service_id)
        qs = mixed_service_mgr.get_provisioned_queryset(service, application_ids=application_ids).order_by(
            param["order_by"]
        )

        page = self.paginator.paginate_queryset(qs, self.request, view=self)
        page_data = []
        # 增强服务按模块级别启用，故需要同时返回应用信息与模块信息
        for obj in page:
            _data = {
                "id": obj.pk,
                "application": obj.module.application,
                "module_name": obj.module.name,
                "created": obj.created,
                "service": obj.service_id,
            }
            page_data.append(_data)
        serializer = slzs.ServiceAttachmentDetailedSLZ(page_data, many=True)
        return self.paginator.get_paginated_response(serializer.data)

    def list_by_category(self, request, code, module_name, category_id):
        """
        获取应用的服务(已启用&未启用)
        [Deprecated] use list_by_module instead
        """
        application = self.get_application()
        module = self.get_module_via_path()
        category = get_object_or_404(ServiceCategory, pk=category_id)

        # Query shared / bound services
        shared_infos = ServiceSharingManager(module).list_shared_info(category.id)
        shared_services = [info.service for info in shared_infos]
        bound_services = list(mixed_service_mgr.list_binded(module, category_id=category.id))

        services_in_category = list(
            mixed_service_mgr.list_by_category(region=application.region, category_id=category.id)
        )
        unbound_services = []
        for svc in services_in_category:
            if svc in bound_services or svc in shared_services:
                continue
            unbound_services.append(svc)

        total = len(bound_services) + len(shared_services) + len(unbound_services)
        return Response(
            {
                "count": total,
                "category": slzs.CategorySLZ(category).data,
                "results": {
                    "bound": slzs.ServiceMinimalSLZ(bound_services, many=True).data,
                    "shared": slzs.SharedServiceInfoSLZ(shared_infos, many=True).data,
                    "unbound": slzs.ServiceMinimalSLZ(unbound_services, many=True).data,
                },
            }
        )

    def list_by_module(self, request, code, module_name):
        """获取指定模块所有分类的应用增强服务(已启用&未启用)"""
        application = self.get_application()
        module = self.get_module_via_path()

        # Query shared / bound services
        shared_infos = list(ServiceSharingManager(module).list_all_shared_info())
        shared_services = [info.service for info in shared_infos]
        bound_services = list(mixed_service_mgr.list_binded(module))

        services_in_region = list(mixed_service_mgr.list_by_region(region=application.region))
        unbound_services = []
        for svc in services_in_region:
            if svc in bound_services or svc in shared_services:
                continue
            unbound_services.append(svc)

        # 已经启用的增强服务
        bound_service_obj_allocations = self._gen_service_obj_allocations(module, bound_services)
        bound_service_infos = list(bound_service_obj_allocations.values())
        # 补充引用当前模块实例的模块信息
        sharing_ref_mgr = SharingReferencesManager(module)
        for svc_info in bound_service_infos:
            svc_info["ref_modules"] = sharing_ref_mgr.list_related_modules(svc_info["service"])

        # 共享其他模块的增强服务
        shared_service_infos = []
        for shared_info in shared_infos:
            svc = shared_info.service
            ref_svc_allocation = self._gen_service_obj_allocations(shared_info.ref_module, services=[svc])[svc.uuid]
            shared_service_infos.append(
                {
                    "service": svc,
                    "module": shared_info.module,
                    "ref_module": shared_info.ref_module,
                    "provision_infos": ref_svc_allocation["provision_infos"],
                    "specifications": ref_svc_allocation["specifications"],
                }
            )

        return Response(
            {
                "bound": slzs.BoundServiceInfoSLZ(bound_service_infos, many=True).data,
                "shared": slzs.SharedServiceInfoWithAllocationSLZ(shared_service_infos, many=True).data,
                "unbound": slzs.ServiceMinimalSLZ(unbound_services, many=True).data,
            }
        )

    @staticmethod
    def _gen_service_obj_allocations(module: Module, services: List[ServiceObj]) -> Dict[str, Any]:
        """生成服务对象分配信息"""
        svc_allocation_map: Dict[str, Dict[str, Any]] = {
            svc.uuid: {"service": svc, "provision_infos": {}, "specifications": []} for svc in services
        }
        for env in module.get_envs():
            rels = mixed_service_mgr.list_all_rels(env.engine_app)
            for rel in rels:
                svc = rel.get_service()
                if svc.uuid not in svc_allocation_map:
                    continue

                alloc = svc_allocation_map[svc.uuid]
                # 补充实例分配信息
                alloc["provision_infos"][env.environment] = rel.is_provisioned()

                # 现阶段所有环境的服务规格一致，若某环境已经获取到配置参数信息，则跳过以免重复
                if alloc["specifications"]:
                    continue

                # 补充配置参数信息
                specs = rel.get_plan().specifications
                for definition in alloc["service"].specifications:
                    result = definition.as_dict()
                    result["value"] = specs.get(definition.name)
                    alloc["specifications"].append(result)

        return svc_allocation_map


class ServiceSetViewSet(viewsets.ViewSet):
    """增强服务集合-查询接口"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @cached_property
    def paginator(self):
        paginator = LimitOffsetPagination()
        paginator.default_limit = 5
        return paginator

    def list_by_category(self, request, category_id):
        """
        根据增强服务分类，查询该分类下的所有增强服务(不区分 region)
        """
        # 保证 category 存在
        category = get_object_or_404(ServiceCategory, pk=category_id)
        all_regions = list(get_all_regions().keys())

        service_sets: Dict[str, ServiceSetGroupByName] = {}
        for region in all_regions:
            services: List[ServiceObj] = list(
                mixed_service_mgr.list_by_category(region=region, category_id=category.id)
            )
            for service in services:
                service_set = service_sets.setdefault(service.name, ServiceSetGroupByName.from_service(service))
                # 初始化 ServiceSet
                service_set.services.append(service)
                service_set.add_enabled_region(region)

        return Response(
            {
                "count": len(service_sets),
                "results": slzs.ServiceSetGroupByNameSLZ(service_sets.values(), many=True).data,
                "regions": all_regions,
            }
        )

    @swagger_auto_schema(query_serializer=slzs.ServiceAttachmentQuerySLZ)
    def list_by_name(self, request, service_name):
        """
        根据增强服务的英文名字，查询所有命名为该名字的增强服务(不区分 region), 并带上绑定服务的实例信息
        """
        # 查询用户具有权限的应用id列表
        application_ids = list(UserApplicationFilter(request.user).filter().values_list("id", flat=True))
        all_regions = get_all_regions().keys()

        serializer = slzs.ServiceAttachmentQuerySLZ(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        param = serializer.data

        service_set = None

        for region in all_regions:
            try:
                service = mixed_service_mgr.find_by_name(region=region, name=service_name)
                if not service_set:
                    service_set = ServiceSetGroupByName.from_service(service)

                # 初始化 service_set
                service_set.services.append(service)
                service_set.add_enabled_region(region)
            except ServiceObjNotFound:
                continue

        if not service_set:
            raise Http404(f"{service_name} not found")

        # 查询与 Services 绑定的 Module
        qs = mixed_service_mgr.get_provisioned_queryset_by_services(
            service_set.services, application_ids=application_ids
        ).order_by(param["order_by"])

        page = self.paginator.paginate_queryset(qs, self.request, view=self)
        # TODO: 查询结果里面同一个应用如果有多个 Module，就会在结果集中出现多次。应该升级为同时返回应用
        # 与模块信息，前端也需要同时升级。
        for obj in page:
            service_set.instances.append(
                {
                    "id": obj.pk,
                    "application": obj.module.application,
                    "module_name": obj.module.name,
                    "created": obj.created,
                    "service": obj.service_id,
                    # 由于增强服务不一定有记录 region 信息, 因此使用 module 的 region 信息
                    "region": obj.module.region,
                }
            )
        return self.paginator.get_paginated_response(slzs.ServiceSetGroupByNameSLZ(service_set).data)


class ServicePlanViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(Response={200: slzs.ServiceSpecificationSLZ}, tags=["增强服务"])
    def retrieve_specifications(self, request, service_id, region):
        """获取一个增强服务的规格组合"""

        service = mixed_service_mgr.get_or_404(service_id, region=region)
        plan_helper = ServicePlansHelper.from_service(service)
        definitions = service.public_specifications
        helper = ServiceSpecificationHelper(definitions, list(plan_helper.get_by_region(region)))
        slz = slzs.ServiceSpecificationSLZ(
            dict(
                definitions=definitions,
                recommended_values=helper.get_recommended_spec().values(),
                values=helper.list_plans_spec_value(),
            )
        )

        return Response(slz.data)


class ServiceSharingViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """与共享增强服务有关的接口"""

    permission_classes = [IsAuthenticated]

    @staticmethod
    def get_service(service_id, application):
        return mixed_service_mgr.get_or_404(service_id, region=application.region)

    @swagger_auto_schema(tags=["增强服务"], response_serializer=MinimalModuleSLZ(many=True))
    @app_action_required(AppAction.BASIC_DEVELOP)
    def list_shareable(self, request, code, module_name, service_id):
        """查看所有可被共享的模块

        客户端可通过该接口，获取当前应用下所有可供共享的模块列表。
        """
        service_obj = self.get_service(service_id, self.get_application())
        module = self.get_module_via_path()
        modules = ServiceSharingManager(module).list_shareable(service_obj)
        return Response(MinimalModuleSLZ(modules, many=True).data)

    @swagger_auto_schema(
        tags=["增强服务"], request_body=slzs.CreateSharedAttachmentsSLZ, responses={201: openapi_empty_response}
    )
    @app_action_required(AppAction.BASIC_DEVELOP)
    def create_shared(self, request, code, module_name, service_id):
        """创建增强服务共享关系

        通过调用该接口创建模块与模块间的共享增强服务关系。要求：

        - 模块只能共享同一应用下的其他模块的增强服务
        - 不能重复共享
        """
        application = self.get_application()
        slz = slzs.CreateSharedAttachmentsSLZ(data=request.data)
        slz.is_valid(raise_exception=True)

        ref_module_name = slz.data["ref_module_name"]
        try:
            ref_module = application.get_module(ref_module_name)
        except ObjectDoesNotExist:
            raise error_codes.CREATE_SHARED_ATTACHMENT_ERROR.f(
                _("模块 {ref_module_name} 不存在").format(ref_module_name=ref_module_name)
            )

        service_obj = self.get_service(service_id, application)
        module = self.get_module_via_path()
        try:
            ServiceSharingManager(module).create(service_obj, ref_module)
        except RuntimeError:
            raise error_codes.CREATE_SHARED_ATTACHMENT_ERROR.f(_("未知错误"))
        except ReferencedAttachmentNotFound:
            raise error_codes.CREATE_SHARED_ATTACHMENT_ERROR.f(
                _("模块 {ref_module_name} 无法被共享").format(ref_module_name=ref_module_name)
            )
        except SharedAttachmentAlreadyExists:
            raise error_codes.CREATE_SHARED_ATTACHMENT_ERROR.f(_("不能重复共享"))
        return Response({}, status.HTTP_201_CREATED)

    @swagger_auto_schema(tags=["增强服务"], response_serializer=slzs.SharedServiceInfoSLZ)
    @app_action_required(AppAction.BASIC_DEVELOP)
    def retrieve(self, request, code, module_name, service_id):
        """查看已创建的共享关系

        客户端可通过该信息跳转被共享的服务实例（`ref_module`）页面。如果无法找到共享关系，接口将返回 404。
        """
        service_obj = self.get_service(service_id, self.get_application())
        module = self.get_module_via_path()
        info = ServiceSharingManager(module).get_shared_info(service_obj)
        if not info:
            raise Http404
        return Response(slzs.SharedServiceInfoSLZ(info).data)

    @swagger_auto_schema(tags=["增强服务"], responses={204: openapi_empty_response})
    @app_action_required(AppAction.MANAGE_ADDONS_SERVICES)
    def destroy(self, request, code, module_name, service_id):
        """解除共享关系

        客户端在需要删除模块共享关系时，调用该接口。
        """
        service_obj = self.get_service(service_id, self.get_application())
        module = self.get_module_via_path()
        ServiceSharingManager(module).destroy(service_obj)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SharingReferencesViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """查看被共享引用的增强服务情况"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @staticmethod
    def get_service(service_id, application):
        return mixed_service_mgr.get_or_404(service_id, region=application.region)

    @swagger_auto_schema(tags=["增强服务"], response_serializer=MinimalModuleSLZ(many=True))
    def list_related_modules(self, request, code, module_name, service_id):
        """查看模块增强服务被共享引用情况

        查看当前模块的增强服务绑定关系，被哪些模块引用。 客户端应该在用户删除增强服务前调用该接口，
        检查待删除的增强服务是否被其他模块共享。假如有其他模块在共享该服务，应该弹出二次确认提醒用户。
        """
        service_obj = self.get_service(service_id, self.get_application())
        module = self.get_module_via_path()
        modules = SharingReferencesManager(module).list_related_modules(service_obj)
        return Response(MinimalModuleSLZ(modules, many=True).data)


class RelatedApplicationsInfoViewSet(viewsets.ViewSet):
    permission_classes = [site_perm_class(SiteAction.SYSAPI_READ_APPLICATIONS)]

    def retrieve_related_applications_info(self, request, db_name):
        """查看 mysql 增强服务的数据库关联的应用信息

        APIGW 调用此接口,根据给定的 mysql 增强服务数据库名称(db_name)检索相关的应用信息。
        """
        store = get_remote_store()
        service_mgr = RemoteServiceMgr(store)
        services = service_mgr.get_mysql_services()
        for service in services:
            service_instance_mgr = RemoteServiceInstanceMgr(store, service)
            app = get_app_by_instance_name(service_instance_mgr, db_name)
            if app is None:
                continue
            return Response(ApplicationMembersInfoSLZ(app).data)
        return Response(status=status.HTTP_200_OK)


class ServiceEngineAppAttachmentViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def list(self, request, code, module_name, service_id):
        """查看增强服务是否导入环境变量"""
        module = self.get_module_via_path()
        envs = module.envs.all()
        service_obj = mixed_service_mgr.get_or_404(service_id, self.get_application().region)
        engine_app_attachments = [
            mixed_service_mgr.get_attachment_by_engine_app(service_obj, env.engine_app) for env in envs
        ]
        return Response(slzs.ServiceEngineAppAttachmentSLZ(engine_app_attachments, many=True).data)

    def update(self, request, code, module_name, service_id):
        """修改增强服务是否导入环境变量"""
        slz = slzs.UpdateServiceEngineAppAttachmentSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        credentials_enabled = data["credentials_enabled"]

        module = self.get_module_via_path()
        envs = module.envs.all()
        service_obj = mixed_service_mgr.get_or_404(service_id, self.get_application().region)
        results = []
        for env in envs:
            attachment = mixed_service_mgr.get_attachment_by_engine_app(service_obj, env.engine_app)
            attachment.credentials_enabled = credentials_enabled
            attachment.save(update_fields=["credentials_enabled"])
            results.append(attachment)

        return Response(slzs.ServiceEngineAppAttachmentSLZ(results, many=True).data)


class UnboundServiceEngineAppAttachmentViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    def list(self, request, code, module_name):
        """查看模块已解绑增强服务，按 service 分类"""
        application = self.get_application()
        module = self.get_module_via_path()

        categorized_rels: Dict[str, List[Dict]] = {}
        for env in module.envs.all():
            for rel in mixed_service_mgr.list_unbound_instance_rels(env.engine_app):
                try:
                    instance = rel.get_instance()
                except SvcInstanceNotFound:
                    # 如果已经回收了，获取不到 instance，跳过
                    continue
                plan = rel.get_plan()

                service_id = rel.db_obj.service_id
                if service_id not in categorized_rels:
                    categorized_rels[service_id] = []

                categorized_rels[service_id].append(
                    {
                        "service_instance": instance,
                        "environment": env.environment,
                        "environment_name": AppEnvName.get_choice_label(env.environment),
                        "service_specs": plan.specifications,
                        "usage": "{}",
                    }
                )

        results = []
        for service_id, rels in categorized_rels.items():
            results.append(
                {"service": mixed_service_mgr.get_or_404(service_id, application.region), "unbound_instances": rels}
            )

        serializer = slzs.UnboundServiceEngineAppAttachmentSLZ(results, many=True)
        return Response(serializer.data)

    def recycle(self, request, code, module_name, service_id, service_instance_id):
        """回收已解绑增强服务"""
        service_obj = mixed_service_mgr.get_or_404(service_id, self.get_application().region)
        unbound_instance = mixed_service_mgr.get_unbound_instance_rel_by_instance_id(service_obj, service_instance_id)
        unbound_instance.recycle_instance()

        return Response()
