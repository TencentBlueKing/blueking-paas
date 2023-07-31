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
import json
import logging
from typing import Dict

from django.http import StreamingHttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from paas_wl.networking.ingress.utils import get_service_dns_name
from paas_wl.utils.views import IgnoreClientContentNegotiation
from paas_wl.workloads.processes.drf_serializers import ListWatcherRespSLZ, WatchEventSLZ, WatchProcessesQuerySLZ
from paas_wl.workloads.processes.watch import ProcInstByEnvListWatcher, WatchEvent
from paasng.accessories.iam.permissions.resources.application import AppAction
from paasng.accounts.permissions.application import application_perm_class
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.utils.rate_limit.constants import UserAction
from paasng.utils.rate_limit.fixed_window import rate_limits_by_user

logger = logging.getLogger(__name__)


class ListAndWatchProcsViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    # Use special negotiation class to accept "text/event-stream" content type
    content_negotiation_class = IgnoreClientContentNegotiation

    @swagger_auto_schema(response_serializer=ListWatcherRespSLZ)
    def list(self, request, code, environment):
        """获取当前进程与进程实例，支持通过 release_id 参数过滤结果"""
        application = self.get_application()

        processes_status = ProcInstByEnvListWatcher(application, environment).list()
        # Get extra infos
        proc_extra_infos = []
        for proc_spec in processes_status.processes:
            proc_extra_infos.append(
                {
                    # TODO: 添加 cnative_proc_specs/process_packages 字段
                    'type': proc_spec.type,
                    'command': proc_spec.runtime.proc_command,
                    'cluster_link': f'http://{get_service_dns_name(proc_spec.app, proc_spec.type)}',
                }
            )

        insts = [inst for proc in processes_status.processes for inst in proc.instances]
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
        return Response(ListWatcherRespSLZ(data).data)

    @rate_limits_by_user(UserAction.WATCH_PROCESS, window_size=60, threshold=10)
    def watch(self, request, code, environment):
        """实时监听进程与进程实例变动情况"""
        application = self.get_application()
        serializer = WatchProcessesQuerySLZ(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        def resp():
            logger.debug(
                'Start watching process, app code=%s, environment=%s, params=%s',
                application.code,
                environment,
                dict(data),
            )
            # 发送初始 ping 事件
            # 避免 stream 无新事件时, 前端请求表现为服务端长时间挂起(无法查看响应头)
            yield 'event: ping\n'
            yield 'data: \n\n'

            stream = ProcInstByEnvListWatcher(application, environment).watch(
                timeout_seconds=data["timeout_seconds"], rv_proc=data["rv_proc"], rv_inst=data["rv_inst"]
            )
            for event in stream:
                e = self.process_event(event)
                yield 'event: message\n'
                yield 'data: {}\n\n'.format(json.dumps(e))

            yield 'id: -1\n'
            yield 'event: EOF\n'
            yield 'data: \n\n'
            logger.info(
                'Watching finished, app code=%s, environment=%s, params=%s', application.code, environment, dict(data)
            )

        return StreamingHttpResponse(resp(), content_type='text/event-stream')

    @staticmethod
    def process_event(event: WatchEvent) -> Dict:
        """Process event payload to Dict of primitive datatypes."""
        return WatchEventSLZ(event).data
