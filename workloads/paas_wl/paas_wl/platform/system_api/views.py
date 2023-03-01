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
import logging

from django.conf import settings
from django.db.models import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet

from paas_wl.cluster.constants import ClusterFeatureFlag
from paas_wl.cluster.utils import get_cluster_by_app, get_default_cluster_by_region
from paas_wl.monitoring.metrics.clients import BkMonitorMetricClient, PrometheusMetricClient
from paas_wl.monitoring.metrics.models import ResourceMetricManager
from paas_wl.platform.applications import models
from paas_wl.platform.applications.models.managers.app_res_ver import AppResVerManager
from paas_wl.platform.auth.permissions import IsInternalAdmin
from paas_wl.platform.system_api import serializers
from paas_wl.release_controller.builder import tasks as builder_task
from paas_wl.release_controller.builder.executor import interrupt_build
from paas_wl.resources.actions.delete import delete_app_resources
from paas_wl.resources.base.bcs_client import BCSClient
from paas_wl.resources.base.exceptions import KubeException
from paas_wl.resources.base.generation import get_latest_mapper_version
from paas_wl.resources.tasks import archive_app, release_app
from paas_wl.resources.utils.app import get_scheduler_client
from paas_wl.utils.error_codes import error_codes
from paas_wl.workloads.processes.controllers import get_processes_status, list_proc_specs
from paas_wl.workloads.processes.models import ProcessSpec, ProcessSpecManager
from paas_wl.workloads.processes.readers import instance_kmodel, process_kmodel

logger = logging.getLogger(__name__)


class SysViewSet(ViewSet):
    """Base class for system APIs, with extra permission check"""

    permission_classes = [IsAuthenticated, IsInternalAdmin]


class SysModelViewSet(ModelViewSet):
    """Base ViewSet for system APIs"""

    permission_classes = [IsAuthenticated, IsInternalAdmin]

    def get_queryset(self):
        return self.model.objects.all()

    def perform_create(self, serializer):
        obj = serializer.save(owner=self.request.user.pk)
        self.post_save(obj)

    def post_save(self, obj):
        """A Hook after object has been saved."""
        raise NotImplementedError


class AppViewSet(SysModelViewSet):
    lookup_field = 'name'
    model = models.App
    serializer_class = serializers.AppSerializer

    def get_queryset(self):
        return self.model.objects.filter(region=self.kwargs['region'])

    def create(self, request, **kwargs):
        request.data['region'] = self.kwargs['region']
        serializer = self.serializer_class(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.AppAlreadyExistsError:
            raise error_codes.APP_ALREADY_EXISTS.f(name=request.data['name'])

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        obj = serializer.save(owner=self.request.user.pk)
        self.post_save(obj)

    def post_save(self, obj):
        # mapper version 概念应该只在 engine 中消化，当前在应用新建后更新
        latest_version = get_latest_mapper_version().version
        AppResVerManager(obj).update(latest_version)

    def update(self, request, **kwargs):
        raise error_codes.ENGINE_NOT_IMPLEMENTED

    def destroy(self, request, *args, **kwargs):
        """虽然 paasng 在上层已经确保部署过的应用不能被删除，
        但是 engine 需要保证自身逻辑的完整性，故删除时仍会尝试删除调度后端资源"""
        app = self.get_object()

        try:
            delete_app_resources(app)
        except Exception as e:
            raise error_codes.APP_DELETE_FAILED.f(f"reason: {e}")

        # Delete some related records manually. Because during API migration, those related data
        # was stored in another database and the `Foreignkey` mechanism can't handle this situation.
        # TODO: Remove below lines when data was fully migrated
        ProcessSpec.objects.filter(engine_app_id=app.pk).delete()

        return super().destroy(request, *args, **kwargs)


class ProcessViewSet(SysModelViewSet):
    """API for processes"""

    lookup_field = 'name'
    model = models.App
    serializer_class = serializers.ProcessSerializer

    def get_queryset(self):
        return self.model.objects.filter(region=self.kwargs['region'])

    def get_process_spec(self, process_type: str):
        engine_app = self.get_object()
        try:
            return ProcessSpec.objects.get(engine_app_id=engine_app.uuid, name=process_type)
        except ProcessSpec.DoesNotExist:
            raise error_codes.PROCESS_OPERATE_FAILED.f(f"进程 '{process_type}' 未定义")

    @staticmethod
    def get_scheduler_client(region):
        cluster = get_default_cluster_by_region(region)
        return get_scheduler_client(cluster_name=cluster.name)

    def list_processes_statuses(self, request, **kwargs):
        """List statuses of all processes"""
        app = self.get_object()
        process_status = get_processes_status(app)
        processes = serializers.ProcessSerializer(process_status, many=True).data
        return Response({"results": processes, "count": len(processes)})

    def list_processes_specs(self, request, *args, **kwargs):
        """List current app's all processes's specs, which is stored in database"""
        app = self.get_object()
        return Response(list_proc_specs(app))

    def sync_specs(self, request, *args, **kwargs):
        """Sync app's specs with given processes"""
        slz = serializers.SyncProcSpecsSerializer(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        # Use only the name of processes, ignore the "command" part
        processes = data["processes"]
        ProcessSpecManager(self.get_object()).sync(processes)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SysAppRelatedViewSet(SysModelViewSet):
    """Base ViewSet for a app_name in url path"""

    permission_classes = [IsAuthenticated, IsInternalAdmin]

    def get_app(self):
        app = get_object_or_404(models.App, region=self.kwargs['region'], name=self.kwargs['name'])
        self.check_object_permissions(self.request, app)
        return app

    def get_queryset(self):
        # Filter to everything belongs to this app
        return self.model.objects.filter(app=self.get_app())

    def create(self, request, **kwargs):
        # Put 'app' field to request.data
        request.data['app'] = self.get_app().uuid
        return super(SysAppRelatedViewSet, self).create(request, **kwargs)

    def perform_create(self, serializer):
        obj = serializer.save()
        self.post_save(obj)


class ProcessInstanceViewSet(SysAppRelatedViewSet):
    """Api for controlling Process's Instances"""

    @swagger_auto_schema(request_body=serializers.WebConsolePostSLZ)
    def create_webconsole(self, request, region, name, process_type, process_instance_name, **kwargs):
        slz = serializers.WebConsolePostSLZ(data=request.data)
        slz.is_valid(True)

        app = self.get_app()
        container_name = slz.validated_data["container_name"]
        if not container_name:
            container_name = process_kmodel.get_by_type(app, type=process_type).main_container_name

        cluster = get_cluster_by_app(app)
        client = BCSClient()
        result = client.api.create_web_console_sessions(
            json={
                'namespace': app.namespace,
                'pod_name': process_instance_name,
                'container_name': container_name,
                'command': slz.validated_data['command'],
                'operator': slz.validated_data['operator'],
            },
            path_params={
                'cluster_id': cluster.annotations['bcs_cluster_id'],
                'project_id_or_code': cluster.annotations['bcs_project_id'],
                'version': 'v4',
            },
        )

        return Response(result)


class BuildViewSet(SysAppRelatedViewSet):
    model = models.Build
    serializer_class = serializers.BuildSerializer

    def perform_create(self, serializer):
        obj = serializer.save(app=self.get_app())
        self.post_save(obj)

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs['uuid'])
        return obj

    def create_placeholder(self, request, **kwargs):
        request.data['app'] = self.get_app().uuid
        slz = serializers.PlaceHolderBuildSerializer(data=request.data)
        slz.is_valid(raise_exception=True)
        obj = slz.save(owner=self.request.user.pk, app=self.get_app())
        return Response(
            serializers.PlaceHolderBuildSerializer(obj).data,
            status=status.HTTP_201_CREATED,
        )


class BuildProcessViewSet(SysAppRelatedViewSet):
    model = models.BuildProcess
    serializer_class = serializers.CreateBuildProcessSerializer
    permission_classes = [IsAuthenticated, IsInternalAdmin]

    def user_interrupt(self, request, region, name, uuid):
        """Interrupt a build process"""
        app = self.get_app()
        bp = get_object_or_404(self.model, app=app, pk=self.kwargs['uuid'])

        if not bp.check_interruption_allowed():
            raise error_codes.INTERRUPTION_NOT_ALLOWED
        if not interrupt_build(bp):
            raise error_codes.INTERRUPTION_FAILED.f("构建可能已结束")
        return Response({})

    def create_build_process(self, request, region, name):
        """Instead of using a project like git-receive, this view
        take a repo address and revision, pull source code down and upload it to BlobStore.
        Then start a slugbuilder service.
        """
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.data
        app = self.get_app()
        image = data.get('image')
        buildpacks = data.get("buildpacks")

        build_process = models.BuildProcess.objects.create(
            owner=self.request.user.pk,
            app=app,
            source_tar_path=data['source_tar_path'],
            revision=data['revision'],
            branch=data['branch'],
            output_stream=models.OutputStream.objects.create(),
            image=image,
            buildpacks=buildpacks,
        )
        builder_task.start_build_process.delay(
            build_process.uuid,
            stream_channel_id=data.get('stream_channel_id'),
            metadata={
                'procfile': data['procfile'],
                'extra_envs': data.get('extra_envs', {}),
                'image': image,
                'buildpacks': build_process.buildpacks_as_build_env(),
            },
        )

        data = serializers.BuildProcessSerializer(build_process).data
        return Response(data, status=status.HTTP_201_CREATED)


class BuildProcessResultViewSet(SysAppRelatedViewSet):
    model = models.BuildProcess
    serializer_class = serializers.BuildProcessResultSerializer
    # Owner can view build result
    permission_classes = [IsAuthenticated, IsInternalAdmin]

    def get_object(self):
        obj = get_object_or_404(
            self.model, app__name=self.kwargs['name'], app__region=self.kwargs['region'], pk=self.kwargs['uuid']
        )
        obj.lines = []
        for line in obj.output_stream.lines.all().order_by('created'):
            obj.lines.append(serializers.LineSerializer(line).data)
        return obj


class ReleaseViewSet(SysAppRelatedViewSet):
    serializer_class = serializers.CreateReleaseSerializer

    def retrieve(self, request, *args, **kwargs):
        release_id = request.data.get('release_id')
        release = get_object_or_404(models.Release, uuid=release_id)

        data = serializers.ReleaseSerializer(release).data
        return Response(data, status=status.HTTP_200_OK)

    def create_release(self, request, region, name):
        """PaaS or CLI launch the release itself for separating build and release"""
        slz = self.serializer_class(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.data

        build = get_object_or_404(models.Build, uuid=data["build"])
        app = build.app

        release = app.release_set.new(owner=self.request.user.pk, build=build, procfile=data["procfile"])
        try:
            release_app(release=release, deployment_id=data["deployment_id"], extra_envs=data["extra_envs"])
        except KubeException as e:
            raise error_codes.APP_RELEASE_FAILED.f(str(e)) from e

        data = serializers.ReleaseSerializer(release).data
        return Response(data, status=status.HTTP_201_CREATED)


class ArchiveViewSet(SysAppRelatedViewSet):
    """This View handle the `archive` operation from paas api server

    'Archive the app' will shutdown all processes in the server.
    """

    def archive(self, request, region, name):
        app = self.get_app()
        operation_id = request.data["operation_id"]

        try:
            archive_app(app, operation_id=operation_id)
        except Exception as e:
            logger.exception("Failed to stop all processes for App<%s>, operation id is: %s", app.name, operation_id)
            raise error_codes.APP_ARCHIVE_FAILED from e

        return Response(status=status.HTTP_204_NO_CONTENT)


class ResourceMetricsViewSet(SysAppRelatedViewSet):
    """应用进程资源使用指标数据相关"""

    @swagger_auto_schema(
        query_serializer=serializers.ResourceMetricsSerializer,
        responses={200: serializers.ResourceMetricsResultSerializer},
    )
    def query(self, request, region, name, process_type, process_instance_name):
        """get instance metrics"""
        serializer = serializers.ResourceMetricsSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.data

        manager = self._get_resource_metric_manager(process_type=process_type)
        try:
            # 请求某个特定 instance 的 metrics
            instance_result = manager.get_instance_metrics(
                time_range=data["time_range"],
                instance_name=process_instance_name,
                resource_types=data["query_metrics"],
            )
        except Exception as e:
            raise error_codes.QUERY_RESOURCE_METRIC_FAILED.f(f"请求 Metric 后端失败: {e}")
        return Response(data=serializers.ResourceMetricsResultSerializer(instance=instance_result, many=True).data)

    @swagger_auto_schema(
        query_serializer=serializers.ResourceMetricsSerializer,
        responses={200: serializers.InstanceMetricsResultSerializer},
    )
    def multi_query(self, request, region, name, process_type):
        """get process metrics"""
        serializer = serializers.ResourceMetricsSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.data

        manager = self._get_resource_metric_manager(process_type=process_type)
        try:
            # 请求所有 instance
            metric_results = manager.get_all_instances_metrics(
                time_range=data["time_range"], resource_types=data["query_metrics"]
            )
        except Exception as e:
            raise error_codes.QUERY_RESOURCE_METRIC_FAILED.f(f"请求 Metric 后端失败: {e}")
        return Response(data=serializers.InstanceMetricsResultSerializer(instance=metric_results, many=True).data)

    def _get_resource_metric_manager(self, process_type):
        # fetch instances of process
        app = self.get_app()

        try:
            cluster = get_cluster_by_app(app)
        except ObjectDoesNotExist:
            raise RuntimeError('no cluster can be found, query aborted')

        if not cluster.bcs_cluster_id:
            raise error_codes.QUERY_RESOURCE_METRIC_FAILED.f("进程所在集群未关联 BCS 信息, 不支持该功能")

        # 不同的指标数据来源依赖配置不同，需要分别检查
        if cluster.has_feature_flag(ClusterFeatureFlag.ENABLE_BK_MONITOR):
            if not settings.BKMONITOR_ENABLED:
                raise error_codes.EDITION_NOT_SUPPORT
            if not cluster.bk_biz_id:
                raise error_codes.QUERY_RESOURCE_METRIC_FAILED.f("进程所在集群未关联 BKCC 业务信息, 不支持该功能")
            metric_client = BkMonitorMetricClient(bk_biz_id=cluster.bk_biz_id)

        else:
            if not settings.MONITOR_CONFIG:
                raise error_codes.EDITION_NOT_SUPPORT
            metric_client = PrometheusMetricClient(**settings.MONITOR_CONFIG["metrics"]["prometheus"])  # type: ignore

        # 获取 EngineApp 对应的进程实例
        try:
            process = process_kmodel.get_by_type(app, process_type)
            process.instances = instance_kmodel.list_by_process_type(app, process_type)
        except Exception:
            raise error_codes.QUERY_RESOURCE_METRIC_FAILED.f("无法获取到进程相关信息")

        if not process.instances:
            raise error_codes.QUERY_RESOURCE_METRIC_FAILED.f("找不到进程实例")

        # 这里默认只有蓝鲸监控数据，暂不支持用户选择数据来源
        return ResourceMetricManager(
            process=process,
            metric_client=metric_client,
            bcs_cluster_id=cluster.bcs_cluster_id,
        )
