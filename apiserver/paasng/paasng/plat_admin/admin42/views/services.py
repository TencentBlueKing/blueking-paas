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
from django.db.transaction import atomic
from django.http.response import Http404
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class
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
from paasng.plat_admin.admin42.serializers.services import (
    PlanObjSLZ,
    PlanWithPreCreatedInstanceSLZ,
    PreCreatedInstanceSLZ,
    ServiceInstanceBindInfoSLZ,
    ServiceObjSLZ,
)
from paasng.plat_admin.admin42.utils.mixins import GenericTemplateView
from paasng.plat_admin.admin42.views.applications import ApplicationDetailBaseView
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.core.region.models import get_all_regions
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


class ApplicationServicesManageViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    """应用增强服务管理-服务管理API"""

    schema = None
    serializer_class = ServiceInstanceBindInfoSLZ
    permission_classes = [IsAuthenticated, site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def list(self, request, code):
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
        return Response(ServiceInstanceBindInfoSLZ(service_instance_list, many=True).data)

    @atomic
    def provision_instance(self, request, code, module_name, environment, service_id):
        module = self.get_module_via_path()
        env = self.get_env_via_path()
        service = mixed_service_mgr.get_or_404(service_id, module.region)

        rel = next(mixed_service_mgr.list_unprovisioned_rels(env.engine_app, service=service), None)
        if not rel:
            raise error_codes.CANNOT_PROVISION_INSTANCE.f(_("当前环境不存在未分配的增强服务实例"))

        rel.provision()
        return Response(status=status.HTTP_201_CREATED)

    @atomic
    def recycle_resource(self, request, code, module_name, service_id, instance_id):
        module = self.get_module_via_path()
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
        slz.is_valid(True)
        data = slz.validated_data
        # 只支持创建本地增强服务
        LocalServiceMgr().create(data)
        return Response(status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        return Response(data=ServiceObjSLZ(mixed_service_mgr.list(), many=True).data)

    def destroy(self, request, pk):
        service = mixed_service_mgr.get_without_region(uuid=pk)
        try:
            mixed_service_mgr.destroy(service)
        except UnsupportedOperationError as e:
            raise error_codes.FEATURE_FLAG_DISABLED.f(str(e))
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, pk):
        try:
            service = mixed_service_mgr.get_without_region(uuid=pk)
        except ServiceObjNotFound:
            raise Http404("ServiceObjNotFound")

        slz = ServiceObjSLZ(data=request.data)
        slz.is_valid(True)
        data = slz.validated_data

        try:
            mixed_service_mgr.update(service, data)
        except UnsupportedOperationError as e:
            raise error_codes.FEATURE_FLAG_DISABLED.f(str(e))
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
        slz.is_valid(True)
        data = slz.validated_data

        service = mixed_service_mgr.get_without_region(uuid=service_id)

        try:
            mixed_plan_mgr.create(service, plan_data=data)
        except UnsupportedOperationError as e:
            raise error_codes.FEATURE_FLAG_DISABLED.f(str(e))

        return Response(status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        return Response(data=PlanObjSLZ(mixed_plan_mgr.list(), many=True).data)

    def destroy(self, request, service_id, plan_id):
        service = mixed_service_mgr.get_without_region(uuid=service_id)

        try:
            mixed_plan_mgr.delete(service, plan_id)
        except UnsupportedOperationError as e:
            raise error_codes.FEATURE_FLAG_DISABLED.f(str(e))
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, service_id, plan_id):
        slz = PlanObjSLZ(data=request.data)
        slz.is_valid(True)
        data = slz.validated_data

        service = mixed_service_mgr.get_without_region(uuid=service_id)

        try:
            mixed_plan_mgr.update(service, plan_id=plan_id, plan_data=data)
        except UnsupportedOperationError as e:
            raise error_codes.FEATURE_FLAG_DISABLED.f(str(e))

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

        kwargs['pagination'] = self.get_pagination_context(self.request)
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
