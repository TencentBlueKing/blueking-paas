# -*- coding: utf-8 -*-
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.filters import SearchFilter
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from paas_wl.admin.mixins import PaginationMixin
from paas_wl.admin.serializers.processes import InstanceSerializer, ProcessSpecBoundInfoSLZ, ProcessSpecPlanSLZ
from paas_wl.platform.applications.permissions import site_perm_class
from paas_wl.platform.auth.permissions import IsInternalAdmin
from paas_wl.platform.system_api.views import SysAppRelatedViewSet
from paas_wl.workloads.processes.constants import ProcessTargetStatus
from paas_wl.workloads.processes.controllers import AppProcessesController
from paas_wl.workloads.processes.models import ProcessSpec, ProcessSpecPlan
from paas_wl.workloads.processes.readers import instance_kmodel


class ProcessSpecPlanManageViewSet(PaginationMixin, ListModelMixin, GenericViewSet):
    """ProcessSpecPlan 管理API"""

    exclude_from_schema = True
    serializer_class = ProcessSpecPlanSLZ
    permission_classes = [site_perm_class("admin:manage:workloads")]
    filter_backends = [SearchFilter]
    search_fields = ['region', 'environment']
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
        slz = self.get_serializer(data=request.data)
        slz.is_valid(True)
        slz.save()
        return Response(slz.validated_data, status=status.HTTP_201_CREATED)

    def edit(self, request, **kwargs):
        """更新已有 ProcessSpecPlan"""
        instance = get_object_or_404(ProcessSpecPlan, pk=self.kwargs["id"])
        slz = self.get_serializer(data=request.data, instance=instance)
        slz.is_valid(True)
        slz.save()

        return Response(slz.validated_data, status=status.HTTP_200_OK)

    def list_binding_app(self, request, **kwargs):
        """获取已有的 AppList"""
        instance = get_object_or_404(ProcessSpecPlan, pk=self.kwargs["id"])
        qs = self.paginate_queryset(instance.processspec_set.all())
        return Response(ProcessSpecBoundInfoSLZ(qs, many=True).data)


class ProcessSpecManageViewSet(SysAppRelatedViewSet):
    """ProcessSpec 管理API"""

    # NOTE: 由于 switch_process_plan 需要给后台调用, 因此需要通过 IsInternalAdmin 权限
    permission_classes = [IsInternalAdmin | site_perm_class("admin:manage:workloads")]

    def switch_process_plan(self, request, region, name, process_type):
        engine_app = self.get_app()
        data = request.data

        if "process_spec_plan_id" in data:
            plan = get_object_or_404(ProcessSpecPlan, pk=data["process_spec_plan_id"])
        else:
            plan_name = data["plan_name"]
            try:
                plan = ProcessSpecPlan.objects.get_by_name(plan_name)
            except ProcessSpecPlan.DoesNotExist:
                raise Http404("No ProcessSpecPlan matches the given name.")

        process_spec, _ = ProcessSpec.objects.get_or_create(
            engine_app_id=engine_app.pk,
            name=process_type,
            defaults={
                "type": 'process',
                "region": region,
                "target_replicas": 1,
                "target_status": ProcessTargetStatus.START,
                "plan": plan,
            },
        )

        process_spec.plan = plan
        process_spec.save(update_fields=["plan", "updated"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    def scale(self, request, region, name, process_type):
        engine_app = self.get_app()
        data = request.data
        process_spec = get_object_or_404(ProcessSpec, engine_app_id=engine_app.pk, name=process_type)
        ctl = AppProcessesController(engine_app)

        if process_spec.target_replicas != int(data["target_replicas"]):
            ctl.scale(process_spec, target_replicas=int(data["target_replicas"]))

        return Response(status=status.HTTP_204_NO_CONTENT)


class ProcessInstanceViewSet(SysAppRelatedViewSet):
    exclude_from_schema = True
    permission_classes = [site_perm_class("admin:manage:workloads")]

    def retrieve(self, request, region, name, process_type, instance_name):
        app = self.get_app()
        inst = instance_kmodel.get(app, instance_name)
        return Response(InstanceSerializer(inst).data)


class AppResourceQuotaViewSet:
    """TODO: 实现应用资源配额视图"""
