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

from django.db.transaction import atomic
from django.http.response import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from paasng.accessories.servicehub.constants import LEGACY_PLAN_ID
from paasng.accessories.servicehub.exceptions import ServiceObjNotFound, SvcAttachmentDoesNotExist
from paasng.accessories.servicehub.manager import LocalServiceMgr, mixed_plan_mgr, mixed_service_mgr
from paasng.accessories.servicehub.remote.exceptions import UnsupportedOperationError
from paasng.accessories.services.models import Plan, PreCreatedInstance, Service, ServiceCategory
from paasng.accessories.services.providers import (
    get_instance_schema_by_service_name,
    get_plan_schema_by_provider_name,
    get_provider_choices,
)
from paasng.core.region.models import get_all_regions
from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class
from paasng.misc.audit.constants import DataType, OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_admin_audit_record
from paasng.plat_admin.admin42.serializers.services import (
    PlanObjSLZ,
    PlanWithPreCreatedInstanceSLZ,
    PreCreatedInstanceSLZ,
    ServiceInstanceBindInfoSLZ,
    ServiceInstanceSLZ,
    ServiceObjSLZ,
)
from paasng.plat_admin.admin42.utils.mixins import GenericTemplateView
from paasng.plat_admin.admin42.views.applications import ApplicationDetailBaseView
from paasng.platform.applications.models import Application
from paasng.utils.error_codes import error_codes


class ApplicationServicesView(ApplicationDetailBaseView):
    """Application应用增强服务页"""

    template_name = "admin42/applications/detail/services.html"
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    name = "增强服务"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        service_instance_list = []
        for module in self.get_application().modules.all():
            for env in module.envs.all():
                for rel in mixed_service_mgr.list_all_rels(engine_app=env.engine_app):
                    instance = None
                    if rel.is_provisioned():
                        instance = rel.get_instance()

                    service_instance_list.append(
                        dict(
                            environment=env,
                            module=env.module.name,
                            instance=instance,
                            service=rel.get_service(),
                            plan=rel.get_plan(),
                        )
                    )

        kwargs["service_instance_list"] = ServiceInstanceBindInfoSLZ(service_instance_list, many=True).data
        return kwargs


class ApplicationServicesManageViewSet(GenericViewSet):
    """应用增强服务管理-服务管理API"""

    schema = None
    serializer_class = ServiceInstanceBindInfoSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def list(self, request, code):
        service_instance_list = []
        application = get_object_or_404(Application, code=code)
        for module in application.modules.all():
            for env in module.envs.all():
                for rel in mixed_service_mgr.list_all_rels(engine_app=env.engine_app):
                    instance = None
                    if rel.is_provisioned():
                        instance = rel.get_instance()

                    service_instance_list.append(
                        dict(
                            environment=env,
                            module=env.module.name,
                            instance=instance,
                            service=rel.get_service(),
                            plan=rel.get_plan(),
                        )
                    )
        return Response(ServiceInstanceBindInfoSLZ(service_instance_list, many=True).data)

    @atomic
    def provision_instance(self, request, code, module_name, environment, service_id):
        application = get_object_or_404(Application, code=code)
        module = application.get_module(module_name)
        env = module.envs.get(environment=environment)
        service = mixed_service_mgr.get_or_404(service_id, module.region)

        rel = next(mixed_service_mgr.list_unprovisioned_rels(env.engine_app, service=service), None)
        if not rel:
            raise error_codes.CANNOT_PROVISION_INSTANCE.f(_("当前环境不存在未分配的增强服务实例"))

        rel.provision()
        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.PROVISION_INSTANCE,
            target=OperationTarget.APP,
            app_code=code,
            module_name=module_name,
            environment=environment,
            data_after=DataDetail(
                type=DataType.RAW_DATA,
                data=ServiceInstanceBindInfoSLZ(
                    environment=env,
                    module=module.name,
                    instance=rel.get_instance(),
                    service=rel.get_service(),
                    plan=rel.get_plan(),
                ).data,
            ),
        )
        return Response(status=status.HTTP_201_CREATED)

    @atomic
    def recycle_resource(self, request, code, module_name, service_id, instance_id):
        application = get_object_or_404(Application, code=code)
        module = application.get_module(module_name)
        service = mixed_service_mgr.get_or_404(service_id, module.region)

        try:
            instance_rel = mixed_service_mgr.get_instance_rel_by_instance_id(service, instance_id)
        except SvcAttachmentDoesNotExist:
            raise Http404

        # 迁移应用不能回收资源
        # 因为关联的方案不能重新分配实例的方案
        # 迁移前先在 paas2.0的 open_paas 表中将数据库信息修改外预期迁移后的数据库信息后，再开始迁移工作
        if instance_rel.get_plan().uuid == LEGACY_PLAN_ID:
            raise error_codes.FEATURE_FLAG_DISABLED.f(_("迁移应用不支持回收增强服务实例"))

        if instance_rel.is_provisioned():
            instance_rel.recycle_resource()
            add_admin_audit_record(
                user=request.user.pk,
                operation=OperationEnum.RECYCLE_RESOURCE,
                target=OperationTarget.APP,
                app_code=code,
                module_name=module_name,
                data_before=DataDetail(
                    type=DataType.RAW_DATA,
                    data={
                        "instance": ServiceInstanceSLZ(instance_rel.get_instance()),
                        "service": ServiceObjSLZ(instance_rel.get_service()),
                        "plan": PlanObjSLZ(instance_rel.get_plan()),
                    },
                ),
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class PlatformServicesView(GenericTemplateView):
    """平台增强服务管理-增强服务页"""

    template_name = "admin42/platformmgr/services.html"
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    name = "服务管理"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)

        kwargs["services"] = ServiceObjSLZ(mixed_service_mgr.list(), many=True).data
        kwargs["region_list"] = [
            dict(value=region.name, text=region.display_name) for region in get_all_regions().values()
        ]
        kwargs["category_list"] = [
            dict(value=category.id, text=category.name) for category in ServiceCategory.objects.all()
        ]
        kwargs["provider_choices"] = get_provider_choices()
        return kwargs


class PlatformServicesManageViewSet(GenericViewSet):
    """平台增强服务管理-服务管理API"""

    schema = None
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def create(self, request, *args, **kwargs):
        slz = ServiceObjSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data
        # 只支持创建本地增强服务
        LocalServiceMgr().create(data)
        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.ADD_ON,
            attribute=data["name"],
            data_after=DataDetail(type=DataType.RAW_DATA, data=data),
        )
        return Response(status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        return Response(data=ServiceObjSLZ(mixed_service_mgr.list(), many=True).data)

    def destroy(self, request, pk):
        service = mixed_service_mgr.get_without_region(uuid=pk)
        data_before = DataDetail(type=DataType.RAW_DATA, data=ServiceObjSLZ(service).data)
        try:
            mixed_service_mgr.destroy(service)
        except UnsupportedOperationError as e:
            raise error_codes.FEATURE_FLAG_DISABLED.f(str(e))

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.ADD_ON,
            attribute=service.name,
            data_before=data_before,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, pk):
        try:
            service = mixed_service_mgr.get_without_region(uuid=pk)
        except ServiceObjNotFound:
            raise Http404("ServiceObjNotFound")

        slz = ServiceObjSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data
        data_before = ServiceObjSLZ(service).data
        # specifications 字段无法序列化，同时 specifications 配置能在 config 字段中看到
        del data_before["specifications"]
        # logo 字段太长，前端比较时会导致浏览器 OOM
        del data_before["logo"]

        try:
            mixed_service_mgr.update(service, data)
        except UnsupportedOperationError as e:
            raise error_codes.FEATURE_FLAG_DISABLED.f(str(e))

        service = mixed_service_mgr.get_without_region(uuid=pk)
        data_after = ServiceObjSLZ(service).data
        del data_after["specifications"]
        del data_after["logo"]
        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.ADD_ON,
            attribute=service.name,
            data_before=DataDetail(type=DataType.RAW_DATA, data=data_before),
            data_after=DataDetail(type=DataType.RAW_DATA, data=data_after),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class PlatformPlanView(GenericTemplateView):
    """平台增强服务管理-方案管理页"""

    template_name = "admin42/platformmgr/plans.html"
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    name = "方案管理"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)

        kwargs["plans"] = PlanObjSLZ(mixed_plan_mgr.list(), many=True).data
        kwargs["services"] = ServiceObjSLZ(mixed_service_mgr.list(), many=True).data
        kwargs["plan_config_schemas"] = {
            str(service.uuid): get_plan_schema_by_provider_name(service.provider_name)
            for service in Service.objects.all()
        }

        kwargs["region_list"] = [
            dict(value=region.name, text=region.display_name) for region in get_all_regions().values()
        ]
        return kwargs


class PlatformPlanManageViewSet(GenericViewSet):
    """平台增强服务管理-方案管理API"""

    schema = None
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def create(self, request, service_id):
        slz = PlanObjSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        service = mixed_service_mgr.get_without_region(uuid=service_id)

        try:
            mixed_plan_mgr.create(service, plan_data=data)
        except UnsupportedOperationError as e:
            raise error_codes.FEATURE_FLAG_DISABLED.f(str(e))

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.ADDON_PLAN,
            attribute=f"{service.name} - {data['name']}",
            data_after=DataDetail(type=DataType.RAW_DATA, data=data),
        )
        return Response(status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        return Response(data=PlanObjSLZ(mixed_plan_mgr.list(), many=True).data)

    def destroy(self, request, service_id, plan_id):
        service = mixed_service_mgr.get_without_region(uuid=service_id)
        # 这里不好直接获取到 plan，通过 service 获取 plan 列表，从列表中找到要删除的 plan
        plans = service.get_plans(is_active=False) + service.get_plans(is_active=True)
        plan = next((plan for plan in plans if plan.uuid == plan_id), None)
        data_before = DataDetail(type=DataType.RAW_DATA, data=PlanObjSLZ(plan).data)

        try:
            mixed_plan_mgr.delete(service, plan_id)
        except UnsupportedOperationError as e:
            raise error_codes.FEATURE_FLAG_DISABLED.f(str(e))

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.DELETE,
            target=OperationTarget.ADDON_PLAN,
            attribute=f"{service.name}" + (f" - {plan.name}" if plan else ""),
            data_before=data_before,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, service_id, plan_id):
        slz = PlanObjSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        service = mixed_service_mgr.get_without_region(uuid=service_id)
        # 这里不好直接获取到 plan，通过 service 获取 plan 列表，从列表中找到要更新的 plan
        plans = service.get_plans(is_active=False) + service.get_plans(is_active=True)
        plan = next((plan for plan in plans if plan.uuid == plan_id), None)
        data_before = DataDetail(type=DataType.RAW_DATA, data=PlanObjSLZ(plan).data)

        try:
            mixed_plan_mgr.update(service, plan_id=plan_id, plan_data=data)
        except UnsupportedOperationError as e:
            raise error_codes.FEATURE_FLAG_DISABLED.f(str(e))

        plans = service.get_plans(is_active=False) + service.get_plans(is_active=True)
        plan = next((plan for plan in plans if plan.uuid == plan_id), None)
        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.ADDON_PLAN,
            attribute=f"{service.name}" + (f" - {plan.name}" if plan else ""),
            data_before=data_before,
            data_after=DataDetail(type=DataType.RAW_DATA, data=PlanObjSLZ(plan).data),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class PreCreatedInstanceView(GenericTemplateView):
    """平台增强服务管理-方案管理页"""

    template_name = "admin42/platformmgr/instance_pools.html"
    serializer_class = PlanWithPreCreatedInstanceSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    name = "资源池管理"

    def get_queryset(self):
        return Plan.objects.filter(
            service__in=[service for service in Service.objects.all() if service.config.get("provider_name") == "pool"]
        )

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        data = self.list(self.request, *self.args, **self.kwargs)

        kwargs["plans"] = data
        kwargs["services"] = ServiceObjSLZ(mixed_service_mgr.list(), many=True).data
        kwargs["instance_schemas"] = {
            str(plan["uuid"]): get_instance_schema_by_service_name(plan["service_name"].lower()) for plan in data
        }

        kwargs["pagination"] = self.get_pagination_context(self.request)
        kwargs["region_list"] = [
            dict(value=region.name, text=region.display_name) for region in get_all_regions().values()
        ]
        return kwargs


class PreCreatedInstanceManageViewSet(ModelViewSet):
    schema = None
    serializer_class = PreCreatedInstanceSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]
    lookup_field = "uuid"

    def get_plan(self):
        return Plan.objects.get(pk=self.kwargs["plan_id"])

    def get_queryset(self):
        qs = PreCreatedInstance.objects.all()
        if "plan_id" in self.kwargs:
            qs.filter(plan=self.get_plan())
        return qs.order_by("created")

    def list(self, request, *args, **kwargs):
        qs = Plan.objects.filter(
            service__in=[service for service in Service.objects.all() if service.config.get("provider_name") == "pool"]
        )
        page = self.paginate_queryset(qs)
        return Response(PlanWithPreCreatedInstanceSLZ(page or qs, many=True).data)
