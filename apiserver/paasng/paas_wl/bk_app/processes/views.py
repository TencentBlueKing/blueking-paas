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

import datetime
import json
import logging
from operator import attrgetter
from typing import Dict, Optional

from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from paas_wl.bk_app.applications.constants import WlAppType
from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.processes.constants import ProcessUpdateType
from paas_wl.bk_app.processes.controllers import get_proc_ctl, judge_operation_frequent
from paas_wl.bk_app.processes.exceptions import (
    InstanceNotFound,
    ProcessNotFound,
    ProcessOperationTooOften,
    ScaleProcessError,
)
from paas_wl.bk_app.processes.models import ProcessSpec
from paas_wl.bk_app.processes.processes import ProcessManager, list_cnative_module_processes_specs
from paas_wl.bk_app.processes.serializers import (
    EventSerializer,
    InstanceLogDownloadInputSLZ,
    InstanceLogQueryInputSLZ,
    ListProcessesQuerySLZ,
    ListWatcherRespSLZ,
    ModuleScopedData,
    ModuleState,
    NamespaceScopedListWatchRespSLZ,
    OperationGroup,
    UpdateProcessSLZ,
    WatchEventSLZ,
    WatchProcessesQuerySLZ,
)
from paas_wl.bk_app.processes.watch import ProcInstByEnvListWatcher, ProcInstByModuleEnvListWatcher, WatchEvent
from paas_wl.infras.resources.base.kres import KDeployment, KPod
from paas_wl.infras.resources.utils.basic import get_client_by_app
from paas_wl.utils.error_codes import error_codes
from paas_wl.utils.views import IgnoreClientContentNegotiation
from paas_wl.workloads.autoscaling.entities import AutoscalingConfig
from paas_wl.workloads.autoscaling.exceptions import AutoscalingUnsupported
from paas_wl.workloads.event.reader import event_kmodel
from paas_wl.workloads.networking.entrance.shim import get_builtin_addr_preferred
from paas_wl.workloads.networking.ingress.utils import get_service_dns_name
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.audit.constants import OperationTarget
from paasng.misc.audit.service import add_app_audit_record
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.bkapp_model import fieldmgr
from paasng.platform.engine.constants import RuntimeType
from paasng.platform.engine.deploy.version import get_env_deployed_version_info
from paasng.platform.engine.models.deployment import Deployment
from paasng.platform.engine.utils.query import DeploymentGetter, OfflineOperationGetter
from paasng.platform.modules.models import Module
from paasng.utils.rate_limit.constants import UserAction
from paasng.utils.rate_limit.fixed_window import rate_limits_by_user

logger = logging.getLogger(__name__)


class ProcessesViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    """适用于所有类型应用，应用进程操作相关视图。"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    _operation_interval: datetime.timedelta = datetime.timedelta(seconds=3)
    _skip_judge_frequent: bool = False

    def update(self, request, code, module_name, environment):
        """操作进程，支持的操作：启动、停止、调整实例数"""
        slz = UpdateProcessSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        module_env = self.get_env_via_path()
        if module_env.is_offlined:
            logger.warning("Unable to update process, environment %s has gone offline.", module_env)
            raise error_codes.CANNOT_OPERATE_PROCESS.f(_("环境未就绪或已下架, 请尝试重新部署"))

        wl_app = self.get_wl_app_via_path()
        process_type = data["process_type"]
        operate_type = data["operate_type"]
        autoscaling = data["autoscaling"]
        target_replicas = data.get("target_replicas")
        scaling_config = data.get("scaling_config")

        # TODO 由于云原生应用去除了对 ProcessSpec model 的依赖, 因此暂时不做操作频率限制, 待后续评估后再添加?
        if wl_app.type == WlAppType.DEFAULT:
            try:
                judge_operation_frequent(wl_app, process_type, self._operation_interval)
            except ProcessOperationTooOften as e:
                raise error_codes.PROCESS_OPERATION_TOO_OFTEN.f(str(e), replace=True)

        self._perform_update(module_env, operate_type, process_type, autoscaling, target_replicas, scaling_config)

        if wl_app.type == WlAppType.DEFAULT:
            try:
                proc_spec = ProcessSpec.objects.get(engine_app_id=module_env.wl_app.uuid, name=process_type)
            except ProcessSpec.DoesNotExist:
                raise error_codes.PROCESS_OPERATE_FAILED.f(f"进程 '{process_type}' 不存在")
            else:
                target_replicas = proc_spec.target_replicas
                target_status = proc_spec.target_status
        else:
            for spec in ProcessManager(module_env).list_processes_specs():
                if spec["name"] == process_type:
                    target_replicas = spec["target_replicas"]
                    target_status = spec["target_status"]
                    break
            else:
                raise error_codes.PROCESS_OPERATE_FAILED.f(f"进程 '{process_type}' 不存在")

        # 审计记录
        add_app_audit_record(
            app_code=self.get_application().code,
            tenant_id=wl_app.tenant_id,
            user=request.user.pk,
            action_id=AppAction.BASIC_DEVELOP,
            module_name=module_env.module.name,
            environment=module_env.environment,
            operation=operate_type,
            target=OperationTarget.PROCESS,
            attribute=process_type,
        )
        return Response(
            status=status.HTTP_200_OK,
            data={"target_replicas": target_replicas, "target_status": target_status},
        )

    def _perform_update(
        self,
        module_env: ModuleEnvironment,
        operate_type: str,
        process_type: str,
        autoscaling: bool,
        target_replicas: Optional[int] = None,
        scaling_config: Optional[AutoscalingConfig] = None,
    ):
        ctl = get_proc_ctl(module_env)
        try:
            if operate_type == ProcessUpdateType.SCALE:
                ctl.scale(process_type, autoscaling, target_replicas, scaling_config)
            elif operate_type == ProcessUpdateType.STOP:
                ctl.stop(process_type)
            elif operate_type == ProcessUpdateType.START:
                ctl.start(process_type)
            else:
                raise error_codes.PROCESS_OPERATE_FAILED.f(f"Invalid operate type {operate_type}")
        except ProcessNotFound as e:
            raise error_codes.PROCESS_OPERATE_FAILED.f(f"进程 '{process_type}' 未定义") from e
        except ScaleProcessError as e:
            raise error_codes.PROCESS_OPERATE_FAILED.f(str(e), replace=True)
        except AutoscalingUnsupported as e:
            raise error_codes.PROCESS_OPERATE_FAILED.f(str(e), replace=True)

        # Set the field manager when it's a scale operation
        if operate_type == ProcessUpdateType.SCALE:
            # Set both the replicas and autoscaling fields at the same time
            fieldmgr.MultiFieldsManager(module_env.module).set_many(
                [
                    fieldmgr.f_proc_replicas(process_type),
                    fieldmgr.f_overlay_replicas(process_type, module_env.environment),
                    fieldmgr.f_overlay_autoscaling(process_type, module_env.environment),
                ],
                fieldmgr.FieldMgrName.WEB_FORM,
            )

    def restart(self, request, code, module_name, environment, process_name):
        """滚动重启进程"""
        env = self.get_env_via_path()
        wl_app = env.wl_app
        with get_client_by_app(wl_app) as client:
            KDeployment(client).restart(name=process_name, namespace=wl_app.namespace)
        return Response(status=status.HTTP_200_OK)


class CNativeListAndWatchProcsViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    """适用于云原生应用，按环境查看应用进程实例相关信息。支持一次查看多个模块。"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    # Use special negotiation class to accept "text/event-stream" content type
    content_negotiation_class = IgnoreClientContentNegotiation

    @swagger_auto_schema(response_serializer=NamespaceScopedListWatchRespSLZ)
    def list(self, request, code, environment):
        """获取当前进程与进程实例, 支持通过 deployment_id 参数过滤结果。"""
        application = self.get_application()
        module_envs = application.envs.filter(environment=environment)

        grouped_data: Dict[str, ModuleScopedData] = {}
        grouped_proc_specs = list_cnative_module_processes_specs(application, environment)

        for module_env in module_envs:
            module = module_env.module
            module_name = module_env.module.name
            is_living, addr = get_builtin_addr_preferred(module_env)
            exposed_url = None
            if is_living and addr:
                exposed_url = addr.url

            build_method, version_info = get_env_deployed_version_info(module_env)
            deployment_getter = DeploymentGetter(env=module_env)
            offline_getter = OfflineOperationGetter(env=module_env)

            grouped_data[module_name] = ModuleScopedData(
                module_name=module_name,
                build_method=build_method,
                state=ModuleState(
                    deployment=OperationGroup(
                        latest=deployment_getter.get_latest_deployment(),
                        latest_succeeded=deployment_getter.get_latest_succeeded(),
                        pending=deployment_getter.get_current_deployment(),
                    ),
                    offline=OperationGroup(
                        latest=offline_getter.get_latest_operation(),
                        latest_succeeded=offline_getter.get_latest_succeeded(),
                        pending=offline_getter.get_current_operation(),
                    ),
                ),
                exposed_url=exposed_url,
                repo_url=self.get_repo_url(module=module) or "--",
                version_info=version_info,
                proc_specs=grouped_proc_specs.get(module_name) or [],
            )

        bkapp_release_id = None
        if deployment_id := request.query_params.get("deployment_id"):
            deployment_obj = get_object_or_404(Deployment, id=deployment_id)
            bkapp_release_id = deployment_obj.bkapp_release_id

        processes_status = ProcInstByEnvListWatcher(application, environment).list()

        for process in processes_status.processes:
            module_name = process.app.module_name
            container = grouped_data[module_name]
            container.processes.append(process)
            if deployment_id:
                if bkapp_release_id:
                    container.instances.extend(
                        [inst for inst in process.instances if inst.version == bkapp_release_id]
                    )
            else:
                container.instances.extend(process.instances)

        return Response(
            NamespaceScopedListWatchRespSLZ(
                {
                    "data": sorted(grouped_data.values(), key=attrgetter("module_name")),
                    "rv_proc": processes_status.rv_proc,
                    "rv_inst": processes_status.rv_inst,
                },
            ).data
        )

    @rate_limits_by_user(UserAction.WATCH_PROCESS, window_size=60, threshold=10)
    def watch(self, request, code, environment):
        """实时监听进程与进程实例变动情况。"""
        application = self.get_application()
        serializer = WatchProcessesQuerySLZ(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        def resp():
            logger.debug(
                "Start watching process, app code=%s, environment=%s, params=%s",
                application.code,
                environment,
                dict(data),
            )
            # 发送初始 ping 事件
            # 避免 stream 无新事件时, 前端请求表现为服务端长时间挂起(无法查看响应头)
            yield "event: ping\n"
            yield "data: \n\n"

            stream = ProcInstByEnvListWatcher(application, environment).watch(
                timeout_seconds=data["timeout_seconds"], rv_proc=data["rv_proc"], rv_inst=data["rv_inst"]
            )
            for event in stream:
                e = self.process_event(event)
                yield "event: message\n"
                yield "data: {}\n\n".format(json.dumps(e))

            yield "id: -1\n"
            yield "event: EOF\n"
            yield "data: \n\n"
            logger.info(
                "Watching finished, app code=%s, environment=%s, params=%s", application.code, environment, dict(data)
            )

        return StreamingHttpResponse(resp(), content_type="text/event-stream")

    @staticmethod
    def process_event(event: WatchEvent) -> Dict:
        """Process event payload to Dict of primitive datatypes."""
        return WatchEventSLZ(event).data

    @staticmethod
    def get_repo_url(module: Module) -> Optional[str]:
        """获取给定模块的"仓库地址",
        对于从源码构建的应用, 仓库地址即源码仓库地址;
        对于从镜像部署的应用, 仓库地址即镜像仓库地址;
        """
        application = module.application
        if (
            application.type == ApplicationType.CLOUD_NATIVE
            and module.build_config.build_method == RuntimeType.CUSTOM_IMAGE
        ):
            return module.build_config.image_repository

        repo = module.get_source_obj()
        if repo is None:
            return None
        return repo.get_repo_url()


class ListAndWatchProcsViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    """适用于普通应用，查看应用进程实例相关信息，支持按模块与环境查看。"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    # Use special negotiation class to accept "text/event-stream" content type
    content_negotiation_class = IgnoreClientContentNegotiation

    @swagger_auto_schema(response_serializer=ListWatcherRespSLZ, query_serializer=ListProcessesQuerySLZ)
    def list(self, request, code, module_name, environment):
        """获取当前进程与进程实例，支持通过 release_id 参数过滤结果"""
        env = self.get_env_via_path()
        wl_app = self.get_wl_app_via_path()
        slz = ListProcessesQuerySLZ(data=request.query_params, context={"wl_app": wl_app})
        slz.is_valid(raise_exception=True)
        release_id = slz.validated_data["release_id"]

        processes_status = ProcInstByModuleEnvListWatcher(env).list()
        # Get extra infos
        proc_extra_infos = []
        for proc_spec in processes_status.processes:
            proc_extra_infos.append(
                {
                    "type": proc_spec.type,
                    "command": proc_spec.runtime.proc_command,
                    "cluster_link": f"http://{get_service_dns_name(proc_spec.app, proc_spec.type)}",
                }
            )

        insts = [inst for proc in processes_status.processes for inst in proc.instances]
        # Filter instances if required
        if release_id:
            release = wl_app.release_set.get(pk=release_id)
            insts = [inst for inst in insts if inst.version == release.version]

        data = {
            "processes": {
                "items": processes_status.processes,
                "extra_infos": proc_extra_infos,
                "metadata": {"resource_version": processes_status.rv_proc},
            },
            "instances": {
                "items": insts,
                "metadata": {"resource_version": processes_status.rv_inst},
            },
            "process_packages": ProcessManager(env).list_processes_specs(),
        }

        return Response(ListWatcherRespSLZ(data).data)

    @rate_limits_by_user(UserAction.WATCH_PROCESS, window_size=30, threshold=8)
    def watch(self, request, code, module_name, environment):
        """实时监听进程与进程实例变动情况"""
        env = self.get_env_via_path()
        wl_app = self.get_wl_app_via_path()
        serializer = WatchProcessesQuerySLZ(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        def resp():
            logger.debug("Start watching process, app=%s, params=%s", wl_app.name, dict(data))
            # 发送初始 ping 事件
            # 避免 stream 无新事件时, 前端请求表现为服务端长时间挂起(无法查看响应头)
            yield "event: ping\n"
            yield "data: \n\n"

            stream = ProcInstByModuleEnvListWatcher(env).watch(
                timeout_seconds=data["timeout_seconds"], rv_proc=data["rv_proc"], rv_inst=data["rv_inst"]
            )
            for event in stream:
                e = self.process_event(wl_app, event)
                yield "event: message\n"
                yield "data: {}\n\n".format(json.dumps(e))

            yield "id: -1\n"
            yield "event: EOF\n"
            yield "data: \n\n"
            logger.info("Watching finished, app=%s, params=%s", wl_app.name, dict(data))

        return StreamingHttpResponse(resp(), content_type="text/event-stream")

    @staticmethod
    def process_event(wl_app: WlApp, event: WatchEvent) -> Dict:
        """Process event payload to Dict of primitive datatypes."""
        return WatchEventSLZ(event, context={"wl_app": wl_app}).data


class InstanceEventsViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    """适用于所有类型应用，应用进程事件相关视图。"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(response_serializer=EventSerializer(many=True))
    def list(self, request, code, module_name, environment, instance_name):
        """获取进程实例的相关事件"""
        wl_app = self.get_wl_app_via_path()

        events = event_kmodel.list_by_app_instance_name(wl_app, instance_name).items
        return Response(EventSerializer(events, many=True).data)


class InstanceManageViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    """适用于所有类型应用，应用进程操作相关视图"""

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    # 下载日志时，默认最大下载的行数一万
    download_log_lines_limit = 10000

    def retrieve_logs(self, request, code, module_name, environment, process_type, process_instance_name):
        """获取进程实例的日志"""
        env = self.get_env_via_path()
        manager = ProcessManager(env)

        slz = InstanceLogQueryInputSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        try:
            logs = manager.get_instance_logs(
                process_type=process_type,
                instance_name=process_instance_name,
                previous=data["previous"],
                tail_lines=data["tail_lines"],
            )
        except InstanceNotFound:
            raise error_codes.PROCESS_INSTANCE_NOT_FOUND

        return Response(status=status.HTTP_200_OK, data=logs.splitlines())

    def download_logs(self, request, code, module_name, environment, process_type, process_instance_name):
        """下载进程实例的日志"""
        env = self.get_env_via_path()
        manager = ProcessManager(env)

        slz = InstanceLogDownloadInputSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        try:
            logs = manager.get_instance_logs(
                process_type=process_type,
                instance_name=process_instance_name,
                previous=data["previous"],
                tail_lines=self.download_log_lines_limit,
            )
        except InstanceNotFound:
            raise error_codes.PROCESS_INSTANCE_NOT_FOUND

        response = HttpResponse(logs, content_type="text/plain")
        log_type = "previous" if data["previous"] else "current"
        response["Content-Disposition"] = f'attachment; filename="{code}-{process_instance_name}-{log_type}-logs.txt"'
        return response

    def restart(self, request, code, module_name, environment, process_instance_name):
        """重启进程实例"""
        env = self.get_env_via_path()
        wl_app = env.wl_app
        with get_client_by_app(wl_app) as client:
            KPod(client).delete(name=process_instance_name, namespace=wl_app.namespace)
        return Response(status=status.HTTP_200_OK)
