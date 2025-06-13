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
from collections import defaultdict
from typing import Any, Dict, List

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paasng.accessories.servicehub import serializers as slzs
from paasng.accessories.servicehub.binding_policy.selector import PlanSelector
from paasng.accessories.servicehub.exceptions import (
    BindServicePlanError,
    ReferencedAttachmentNotFound,
    ServiceObjNotFound,
    SharedAttachmentAlreadyExists,
    UnboundSvcAttachmentDoesNotExist,
)
from paasng.accessories.servicehub.manager import mixed_service_mgr
from paasng.accessories.servicehub.remote.manager import (
    RemoteServiceInstanceMgr,
    RemoteServiceMgr,
    get_app_by_instance_name,
)
from paasng.accessories.servicehub.remote.store import get_remote_store
from paasng.accessories.servicehub.services import ServiceObj
from paasng.accessories.servicehub.sharing import ServiceSharingManager, SharingReferencesManager
from paasng.accessories.services.models import ServiceCategory
from paasng.core.tenant.user import get_tenant
from paasng.infras.accounts.constants import FunctionType
from paasng.infras.accounts.models import make_verifier
from paasng.infras.accounts.permissions.application import (
    app_view_actions_perm,
    application_perm_class,
)
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.infras.sysapi_client.constants import ClientAction
from paasng.infras.sysapi_client.roles import sysapi_client_perm_class
from paasng.misc.audit.constants import OperationEnum, OperationTarget
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

    permission_classes = [
        IsAuthenticated,
        app_view_actions_perm(
            {"unbind": AppAction.MANAGE_ADDONS_SERVICES},
            default_action=AppAction.BASIC_DEVELOP,
        ),
    ]

    @staticmethod
    def get_service(service_id, application):
        return mixed_service_mgr.get_or_404(service_id)

    def _get_application_by_code(self, application_code):
        application = get_object_or_404(Application, code=application_code)
        # NOTE: 必须检查是否具有操作 app 的权限
        self.check_object_permissions(self.request, application)
        return application

    @transaction.atomic
    @swagger_auto_schema(request_body=slzs.CreateAttachmentSLZ, response_serializer=slzs.ServiceAttachmentSLZ)
    def bind(self, request):
        """创建蓝鲸应用与增强服务的绑定关系"""
        serializer = slzs.CreateAttachmentSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.data
        application = self._get_application_by_code(data["code"])
        service_obj = self.get_service(data["service_id"], application)
        module = application.get_module(data.get("module_name", None))

        try:
            rel_pk = mixed_service_mgr.bind_service(
                service_obj,
                module,
                plan_id=data["plan_id"],
                env_plan_id_map=data["env_plan_id_map"],
            )
        except BindServicePlanError as e:
            logger.warning("No plans can be found for service %s, environment: %s.", service_obj.uuid, str(e))
            raise error_codes.CANNOT_BIND_SERVICE.f(_("获取可用服务方案失败"))
        except Exception:
            logger.exception("bind service %s to module %s error.", service_obj.uuid, module.name)
            raise error_codes.CANNOT_BIND_SERVICE.f("Unknown error")

        for env in module.envs.all():
            for rel in mixed_service_mgr.list_unprovisioned_rels(env.engine_app, service_obj):
                plan = rel.get_plan()
                if plan.is_eager:
                    rel.provision()

        SERVICE_BIND_COUNTER.labels(service=service_obj.name).inc()
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
            tenant_id=application.tenant_id,
            user=request.user.pk,
            action_id=AppAction.BASIC_DEVELOP,
            operation=OperationEnum.ENABLE,
            target=OperationTarget.ADD_ON,
            attribute=service_obj.name,
            module_name=module.name,
            data_after=DataDetail(data=service_obj.config),
        )
        return Response(serializer.data)

    def retrieve(self, request, code, module_name, service_id):
        """查看应用模块与增强服务的绑定关系详情。

        - `plans` 字段包含每个环境的方案详情
        """
        application = self.get_application()
        module = self.get_module_via_path()
        service = self.get_service(service_id, application)

        # 如果模块与增强服务之间没有绑定关系，直接返回 404 状态码
        if not mixed_service_mgr.module_is_bound_with(service, module):
            raise Http404

        results = []
        plans = {}
        for env in module.envs.all():
            for rel in mixed_service_mgr.list_provisioned_rels(env.engine_app, service=service):
                instance = rel.get_instance()
                results.append(
                    {
                        "service_instance": instance,
                        "environment": env.environment,
                        "environment_name": AppEnvName.get_choice_label(env.environment),
                        "usage": "{}",
                    }
                )

            for rel in mixed_service_mgr.list_all_rels(env.engine_app, service_id=service.uuid):
                plans[env.environment] = slzs.PlanForDisplaySLZ(rel.get_plan()).data
                # Only read the first one
                break

        serializer = slzs.ServiceInstanceInfoSLZ(results, many=True)
        return Response({"count": len(results), "results": serializer.data, "plans": plans})

    @swagger_auto_schema(response_serializer=slzs.PossiblePlansOutputSLZ)
    def list_possible_plans(self, request, code, module_name, service_id):
        """获取应用模块绑定服务时，可能的方案详情，主要由客户端在绑定前调用。关键逻辑：

        - 当 `has_multiple_plans` 为 False 时，无需其他操作，可直接继续完成绑定
        - 当 `has_multiple_plans` 为 True 时，表示存在多个可选方案，此时需要引导用户完成选择
            - `static_plans` 非空时：表示所有环境的方案一致，使用该列表作为可选项
            - `env_specific_plans` 非空时：表示不同环境的方案不一致，使用该字典作为可选项，此时
              可能需要区分环境来展示多个可选项
        """
        application = self.get_application()
        module = self.get_module_via_path()
        service = self.get_service(service_id, application)

        possible_plans = PlanSelector().list_possible_plans(service, module)
        has_multi = possible_plans.has_multiple_plans()
        if not has_multi:
            # 当不存在多个可选方案时，无需返回更多信息，因为可以直接完成绑定
            slz = slzs.PossiblePlansOutputSLZ({"has_multiple_plans": False})
            return Response(slz.data)

        def _plans_to_data(plans):
            return [{"uuid": p.uuid, "name": p.name, "description": p.description} for p in plans]

        # Set the plans data
        data: Dict[str, Any] = {"has_multiple_plans": has_multi}
        if static_plans := possible_plans.get_static_plans():
            data["static_plans"] = _plans_to_data(static_plans)
        elif env_plans := possible_plans.get_env_specific_plans():
            data["env_specific_plans"] = {env: _plans_to_data(plans) for env, plans in env_plans.items()}

        slz = slzs.PossiblePlansOutputSLZ(data)
        return Response(slz.data)

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
            tenant_id=application.tenant_id,
            user=request.user.pk,
            action_id=AppAction.MANAGE_ADDONS_SERVICES,
            operation=OperationEnum.DISABLE,
            target=OperationTarget.ADD_ON,
            attribute=service.name,
            module_name=module_name,
            data_before=DataDetail(data=service.config if service else None),
        )
        return Response(status=status.HTTP_200_OK)

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
        service = mixed_service_mgr.get(uuid=service_id)
        serializer = self.serializer_class(service)
        return Response({"result": serializer.data})

    def list_by_template(self, request, template):
        """根据初始模板获取相关增强服务"""
        tmpl = Template.objects.get(name=template, type=TemplateType.NORMAL)
        services = {}
        for name in tmpl.preset_services_config:
            # INFO: 之前的版本会读取 preset_services_config 中的 value 作为服务信息，用来
            # 当成 Specs 来筛选服务的 Plan，目前已废弃。
            try:
                service = mixed_service_mgr.find_by_name(name)
            except ServiceObjNotFound:
                logger.exception("Failed to get enhanced service <%s> preset in template <%s>", name, template)
                continue

            slz = slzs.ServiceSimpleFieldsSLZ(
                {
                    "uuid": service.uuid,
                    "name": service.name,
                    "display_name": service.display_name,
                    "description": service.description,
                    "category": service.category,
                }
            )
            services[service.name] = slz.data

        return Response({"result": services})

    @swagger_auto_schema(query_serializer=slzs.ServiceAttachmentQuerySLZ())
    def list_related_apps(self, request, service_id):
        """获取服务绑定的所有应用"""
        serializer = slzs.ServiceAttachmentQuerySLZ(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        param = serializer.data
        application_ids = list(
            Application.objects.filter_by_user(request.user, get_tenant(request.user).id).values_list("id", flat=True)
        )

        service = mixed_service_mgr.get(uuid=service_id)
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
        module = self.get_module_via_path()
        category = get_object_or_404(ServiceCategory, pk=category_id)

        # Query shared / bound services
        shared_infos = ServiceSharingManager(module).list_shared_info(category.id)
        shared_services = [info.service for info in shared_infos]
        bound_services = list(mixed_service_mgr.list_binded(module, category_id=category.id))

        services_in_category = list(mixed_service_mgr.list_by_category(category_id=category.id))
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
        module = self.get_module_via_path()

        # Query shared / bound services
        shared_infos = list(ServiceSharingManager(module).list_all_shared_info())
        shared_services = [info.service for info in shared_infos]
        bound_services = list(mixed_service_mgr.list_binded(module))

        services = list(mixed_service_mgr.list_visible())
        unbound_services = []
        for svc in services:
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
            svc.uuid: {"service": svc, "provision_infos": {}, "plans": {}} for svc in services
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
                alloc["plans"][env.environment] = rel.get_plan()
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
        """根据增强服务分类，查询该分类下的所有增强服务。"""
        # 保证 category 存在
        category = get_object_or_404(ServiceCategory, pk=category_id)
        services: List[ServiceObj] = list(mixed_service_mgr.list_by_category(category_id=category.id))
        return Response(
            {
                "count": len(services),
                "results": slzs.ServiceWithInstsSLZ(services, many=True).data,
            }
        )

    @swagger_auto_schema(query_serializer=slzs.ServiceAttachmentQuerySLZ())
    def list_by_name(self, request, service_name):
        """根据增强服务的英文名字，查询所有命名为该名字的增强服务, 并带上绑定服务的实例信息"""
        # 查询用户具有权限的应用id列表
        application_ids = list(UserApplicationFilter(request.user).filter().values_list("id", flat=True))

        serializer = slzs.ServiceAttachmentQuerySLZ(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        param = serializer.data

        try:
            service = mixed_service_mgr.find_by_name(name=service_name)
        except ServiceObjNotFound:
            raise Http404(f"{service_name} not found")

        # 查询与 Services 绑定的 Module
        qs = mixed_service_mgr.get_provisioned_queryset(service, application_ids=application_ids).order_by(
            param["order_by"]
        )

        instances = []
        page = self.paginator.paginate_queryset(qs, self.request, view=self)
        # TODO: 查询结果里面同一个应用如果有多个 Module，就会在结果集中出现多次。应该升级为同时返回应用
        # 与模块信息，前端也需要同时升级。
        for obj in page:
            instances.append(
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
        service.instances = instances  # type: ignore
        return self.paginator.get_paginated_response(slzs.ServiceWithInstsSLZ(service).data)


class ServiceSharingViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """与共享增强服务有关的接口"""

    permission_classes = [
        IsAuthenticated,
        app_view_actions_perm(
            {"destroy": AppAction.MANAGE_ADDONS_SERVICES},
            default_action=AppAction.BASIC_DEVELOP,
        ),
    ]

    @staticmethod
    def get_service(service_id, application):
        return mixed_service_mgr.get_or_404(service_id)

    @swagger_auto_schema(tags=["增强服务"], response_serializer=MinimalModuleSLZ(many=True))
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
        return mixed_service_mgr.get_or_404(service_id)

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
    permission_classes = [sysapi_client_perm_class(ClientAction.READ_APPLICATIONS)]

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
        service_obj = mixed_service_mgr.get_or_404(service_id)
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
        service_obj = mixed_service_mgr.get_or_404(service_id)
        results = []
        for env in envs:
            attachment = mixed_service_mgr.get_attachment_by_engine_app(service_obj, env.engine_app)
            attachment.credentials_enabled = credentials_enabled
            attachment.save(update_fields=["credentials_enabled"])
            results.append(attachment)

        return Response(slzs.ServiceEngineAppAttachmentSLZ(results, many=True).data)


class UnboundServiceEngineAppAttachmentViewSet(viewsets.ViewSet, ApplicationCodeInPathMixin):
    """已解绑待回收增强服务实例相关API"""

    permission_classes = [
        IsAuthenticated,
        app_view_actions_perm(
            {"list_by_module": AppAction.BASIC_DEVELOP},
            default_action=AppAction.MANAGE_ADDONS_SERVICES,
        ),
    ]

    @swagger_auto_schema(tags=["增强服务"], response_serializer=slzs.UnboundServiceEngineAppAttachmentSLZ(many=True))
    def list_by_module(self, request, code, module_name):
        """查看模块所有已解绑增强服务实例，按增强服务归类"""
        module = self.get_module_via_path()

        categorized_rels = defaultdict(list)
        for env in module.envs.all():
            for rel in mixed_service_mgr.list_unbound_instance_rels(env.engine_app):
                instance = rel.get_instance()
                if not instance:
                    # 如果已经回收了，获取不到 instance，跳过
                    continue

                categorized_rels[str(rel.db_obj.service_id)].append(
                    {
                        "instance_id": rel.db_obj.service_instance_id,
                        "service_instance": instance,
                        "environment": env.environment,
                        "environment_name": AppEnvName.get_choice_label(env.environment),
                    }
                )

        results = []
        for service_id, rels in categorized_rels.items():
            results.append({"service": mixed_service_mgr.get_or_404(service_id), "unbound_instances": rels})

        serializer = slzs.UnboundServiceEngineAppAttachmentSLZ(results, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(tags=["增强服务"], query_serializer=slzs.DeleteUnboundServiceEngineAppAttachmentSLZ)
    def delete(self, request, code, module_name, service_id):
        """回收已解绑增强服务"""
        slz = slzs.DeleteUnboundServiceEngineAppAttachmentSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        service_obj = mixed_service_mgr.get_or_404(service_id)
        try:
            unbound_instance = mixed_service_mgr.get_unbound_instance_rel_by_instance_id(
                service_obj, data["instance_id"]
            )
        except UnboundSvcAttachmentDoesNotExist:
            raise Http404

        unbound_instance.recycle_resource()

        return Response()

    @swagger_auto_schema(tags=["增强服务"], request_body=slzs.RetrieveUnboundServiceSensitiveFieldSLZ)
    def retrieve_sensitive_field(self, request, code, module_name, service_id):
        """验证验证码查看解绑实例的敏感信息字段"""
        serializer = slzs.RetrieveUnboundServiceSensitiveFieldSLZ(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        # 验证验证码
        if settings.ENABLE_VERIFICATION_CODE:
            verifier = make_verifier(request.session, FunctionType.RETRIEVE_UNBOUND_SERVICE_SENSITIVE_FIELD.value)
            is_valid = verifier.validate(data["verification_code"])
            if not is_valid:
                raise ValidationError({"verification_code": [_("验证码错误")]})
        # 部分版本没有发送通知的渠道可置：跳过验证码校验步骤
        else:
            logger.warning(
                "Verification code functionality is not currently supported. Returning the sensitive field directly."
            )

        service_obj = mixed_service_mgr.get_or_404(service_id)

        try:
            unbound_instance_rel = mixed_service_mgr.get_unbound_instance_rel_by_instance_id(
                service_obj, data["instance_id"]
            )
        except UnboundSvcAttachmentDoesNotExist:
            raise Http404

        instance = unbound_instance_rel.get_instance()
        if not instance:
            raise NotFound(detail="Resource has been recycled.", code=404)

        credentials = instance.credentials
        if data["field_name"] in instance.should_remove_fields and data["field_name"] in credentials:
            return Response(credentials[data["field_name"]])
        return Response()
