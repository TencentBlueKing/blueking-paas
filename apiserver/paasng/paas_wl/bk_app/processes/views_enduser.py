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
import datetime
import json
import logging
from typing import Dict, Optional

from django.http import StreamingHttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from paas_wl.core.signals import new_operation_happened
from paas_wl.workloads.networking.ingress.utils import get_service_dns_name
from paas_wl.bk_app.applications.constants import WlAppType
from paas_wl.bk_app.applications.models import WlApp
from paas_wl.utils.error_codes import error_codes
from paas_wl.utils.views import IgnoreClientContentNegotiation
from paas_wl.workloads.autoscaling.exceptions import AutoscalingUnsupported
from paas_wl.workloads.autoscaling.models import AutoscalingConfig
from paas_wl.bk_app.processes.constants import ProcessUpdateType
from paas_wl.bk_app.processes.controllers import get_proc_ctl, judge_operation_frequent
from paas_wl.bk_app.processes.drf_serializers import (
    ListProcessesQuerySLZ,
    ListWatcherRespSLZ,
    UpdateProcessSLZ,
    WatchEventSLZ,
    WatchProcessesQuerySLZ,
)
from paas_wl.bk_app.processes.exceptions import ProcessNotFound, ProcessOperationTooOften, ScaleProcessError
from paas_wl.bk_app.processes.shim import ProcessManager
from paas_wl.bk_app.processes.watch import ProcInstByModuleEnvListWatcher, WatchEvent
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.applications.models import ModuleEnvironment
from paasng.misc.operations.constant import OperationType
from paasng.utils.rate_limit.constants import UserAction
from paasng.utils.rate_limit.fixed_window import rate_limits_by_user

logger = logging.getLogger(__name__)


class ProcessesViewSet(GenericViewSet, ApplicationCodeInPathMixin):
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
            raise error_codes.CANNOT_OPERATE_PROCESS.f('环境已下架')

        wl_app = self.get_wl_app_via_path()
        process_type = data['process_type']
        operate_type = data['operate_type']
        autoscaling = data['autoscaling']
        target_replicas = data.get('target_replicas')
        scaling_config = data.get('scaling_config')

        try:
            judge_operation_frequent(wl_app, process_type, self._operation_interval)
        except ProcessOperationTooOften as e:
            raise error_codes.PROCESS_OPERATION_TOO_OFTEN.f(str(e), replace=True)

        self._perform_update(module_env, operate_type, process_type, autoscaling, target_replicas, scaling_config)

        # Create application operation log
        op_type = self.get_logging_operate_type(operate_type)
        if op_type:
            try:
                new_operation_happened.send(
                    sender=module_env,
                    env=module_env,
                    operate_type=op_type,
                    operator=request.user.pk,
                    extra_values={"process_type": process_type, "env_name": module_env.environment},
                )
            except Exception:
                logger.exception('Error creating app operation log')

        return Response(status=status.HTTP_200_OK)

    @staticmethod
    def get_logging_operate_type(type_: str) -> Optional[int]:
        """Get the type of application operation"""
        return {'start': OperationType.PROCESS_START.value, 'stop': OperationType.PROCESS_STOP.value}.get(type_, None)

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


class ListAndWatchProcsViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    # Use special negotiation class to accept "text/event-stream" content type
    content_negotiation_class = IgnoreClientContentNegotiation

    @swagger_auto_schema(response_serializer=ListWatcherRespSLZ, query_serializer=ListProcessesQuerySLZ)
    def list(self, request, code, module_name, environment):
        """获取当前进程与进程实例，支持通过 release_id 参数过滤结果"""
        env = self.get_env_via_path()
        wl_app = self.get_wl_app_via_path()
        slz = ListProcessesQuerySLZ(data=request.query_params, context={'wl_app': wl_app})
        slz.is_valid(raise_exception=True)
        release_id = slz.validated_data['release_id']

        processes_status = ProcInstByModuleEnvListWatcher(env).list()
        # Get extra infos
        proc_extra_infos = []
        for proc_spec in processes_status.processes:
            proc_extra_infos.append(
                {
                    'type': proc_spec.type,
                    'command': proc_spec.runtime.proc_command,
                    'cluster_link': f'http://{get_service_dns_name(proc_spec.app, proc_spec.type)}',
                }
            )

        insts = [inst for proc in processes_status.processes for inst in proc.instances]
        # Filter instances if required
        if release_id:
            release = wl_app.release_set.get(pk=release_id)
            insts = [inst for inst in insts if inst.version == release.version]

        data = {
            'processes': {
                'items': processes_status.processes,
                'extra_infos': proc_extra_infos,
                'metadata': {'resource_version': processes_status.rv_proc},
            },
            'instances': {
                'items': insts,
                'metadata': {'resource_version': processes_status.rv_inst},
            },
        }
        processes_specs = ProcessManager(env).list_processes_specs()
        if wl_app.type == WlAppType.CLOUD_NATIVE:
            data["cnative_proc_specs"] = processes_specs
        else:
            data["process_packages"] = processes_specs

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
            logger.debug('Start watching process, app=%s, params=%s', wl_app.name, dict(data))
            # 发送初始 ping 事件
            # 避免 stream 无新事件时, 前端请求表现为服务端长时间挂起(无法查看响应头)
            yield 'event: ping\n'
            yield 'data: \n\n'

            stream = ProcInstByModuleEnvListWatcher(env).watch(
                timeout_seconds=data["timeout_seconds"], rv_proc=data["rv_proc"], rv_inst=data["rv_inst"]
            )
            for event in stream:
                e = self.process_event(wl_app, event)
                yield 'event: message\n'
                yield 'data: {}\n\n'.format(json.dumps(e))

            yield 'id: -1\n'
            yield 'event: EOF\n'
            yield 'data: \n\n'
            logger.info('Watching finished, app=%s, params=%s', wl_app.name, dict(data))

        return StreamingHttpResponse(resp(), content_type='text/event-stream')

    @staticmethod
    def process_event(wl_app: WlApp, event: WatchEvent) -> Dict:
        """Process event payload to Dict of primitive datatypes."""
        return WatchEventSLZ(event, context={"wl_app": wl_app}).data
