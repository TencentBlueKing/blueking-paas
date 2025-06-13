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

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.filters import SearchFilter
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from paas_wl.apis.admin.mixins import PaginationMixin
from paas_wl.apis.admin.serializers.processes import InstanceSerializer, ProcessSpecBoundInfoSLZ, ProcessSpecPlanSLZ
from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.processes.constants import ProcessTargetStatus
from paas_wl.bk_app.processes.controllers import get_proc_ctl
from paas_wl.bk_app.processes.models import ProcessSpec, ProcessSpecPlan
from paas_wl.bk_app.processes.readers import instance_kmodel
from paasng.infras.accounts.permissions.global_site import SiteAction, site_perm_class
from paasng.misc.audit.constants import OperationEnum, OperationTarget
from paasng.misc.audit.service import DataDetail, add_admin_audit_record
from paasng.platform.applications.models import ModuleEnvironment


def get_env_by_wl_app(wl_app: WlApp) -> ModuleEnvironment:
    return ModuleEnvironment.objects.get(engine_app_id=wl_app.pk)


class ProcessSpecPlanManageViewSet(PaginationMixin, ListModelMixin, GenericViewSet):
    """ProcessSpecPlan 管理API"""

    exclude_from_schema = True
    serializer_class = ProcessSpecPlanSLZ
    permission_classes = [site_perm_class(SiteAction.MANAGE_PLATFORM)]
    filter_backends = [SearchFilter]
    search_fields = ["environment"]
    queryset = ProcessSpecPlan.objects.all()

    def _list_data(self):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page or queryset, many=True)
        return serializer.data

    def get_context_data(self, request):
        self.paginator.default_limit = 10
        return Response(
            data={
                "process_spec_plan_list": self._list_data(),
                "pagination": self.get_pagination_context(self.request),
            }
        )

    def create(self, request, **kwargs):
        """创建 ProcessSpecPlan"""
        slz = ProcessSpecPlanSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        slz.save()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.CREATE,
            target=OperationTarget.PROCESS_SPEC_PLAN,
            data_after=DataDetail(data=slz.validated_data),
        )
        return Response(slz.validated_data, status=status.HTTP_201_CREATED)

    def edit(self, request, **kwargs):
        """更新已有 ProcessSpecPlan"""
        plan = get_object_or_404(ProcessSpecPlan, pk=self.kwargs["id"])
        data_before = DataDetail(data=ProcessSpecPlanSLZ(plan).data)

        slz = ProcessSpecPlanSLZ(data=request.data, instance=plan)
        slz.is_valid(raise_exception=True)
        slz.save()

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY,
            target=OperationTarget.PROCESS_SPEC_PLAN,
            data_before=data_before,
            data_after=DataDetail(data=ProcessSpecPlanSLZ(plan).data),
        )
        return Response(slz.validated_data, status=status.HTTP_200_OK)

    def list_binding_app(self, request, **kwargs):
        """获取已有的 AppList"""
        plan = get_object_or_404(ProcessSpecPlan, pk=self.kwargs["id"])
        qs = self.paginate_queryset(plan.processspec_set.all())
        return Response(ProcessSpecBoundInfoSLZ(qs, many=True).data)


class ProcessSpecManageViewSet(GenericViewSet):
    """ProcessSpec 管理API"""

    # NOTE: 由于 switch_process_plan 需要给后台调用, 因此需要通过 IsInternalAdmin 权限
    permission_classes = [site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def get_app(self):
        app = get_object_or_404(WlApp, name=self.kwargs["name"])
        self.check_object_permissions(self.request, app)
        return app

    def switch_process_plan(self, request, name, process_type):
        wl_app = self.get_app()
        data = request.data

        if "process_spec_plan_id" in data:
            plan = get_object_or_404(ProcessSpecPlan, pk=data["process_spec_plan_id"])
        else:
            plan_name = data["plan_name"]
            try:
                plan = ProcessSpecPlan.objects.get_by_name(plan_name)
            except ProcessSpecPlan.DoesNotExist:
                raise Http404("No ProcessSpecPlan matches the given name.")

        defaults = {
            "type": "process",
            "target_replicas": 1,
            "target_status": ProcessTargetStatus.START,
            "plan": plan,
            "tenant_id": wl_app.tenant_id,
        }

        process_spec, _ = ProcessSpec.objects.get_or_create(
            engine_app_id=wl_app.pk,
            name=process_type,
            defaults=defaults,
        )
        # 记录目前使用的 plan 名称（操作审计用）
        cur_plan_name = process_spec.plan.name

        process_spec.plan = plan
        process_spec.save(update_fields=["plan", "updated"])

        add_admin_audit_record(
            user=request.user.pk,
            operation=OperationEnum.MODIFY_PLAN,
            target=OperationTarget.PROCESS,
            attribute=f"{wl_app.name}:{process_type}",
            data_before=DataDetail(data={"plan": cur_plan_name}),
            data_after=DataDetail(data={"plan": plan.name}),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def scale(self, request, name, process_type):
        wl_app = self.get_app()
        data = request.data
        process_spec = get_object_or_404(ProcessSpec, engine_app_id=wl_app.pk, name=process_type)
        ctl = get_proc_ctl(get_env_by_wl_app(wl_app))

        if process_spec.target_replicas != int(data["target_replicas"]):
            data_before = DataDetail(data={"replicas": process_spec.target_replicas})
            ctl.scale(process_spec.name, target_replicas=int(data["target_replicas"]))
            add_admin_audit_record(
                user=request.user.pk,
                operation=OperationEnum.SCALE,
                target=OperationTarget.PROCESS,
                attribute=wl_app.name,
                data_before=data_before,
                data_after=DataDetail(data={"replicas": data["target_replicas"]}),
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class ProcessInstanceViewSet(GenericViewSet):
    exclude_from_schema = True
    permission_classes = [site_perm_class(SiteAction.MANAGE_PLATFORM)]

    def get_app(self):
        app = get_object_or_404(WlApp, name=self.kwargs["name"])
        self.check_object_permissions(self.request, app)
        return app

    def retrieve(self, request, name, process_type, instance_name):
        app = self.get_app()
        inst = instance_kmodel.get(app, instance_name)
        return Response(InstanceSerializer(inst).data)
