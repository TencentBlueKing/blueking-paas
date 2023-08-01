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
from dataclasses import dataclass, field
from operator import attrgetter
from typing import Dict, List, Optional

from django.http import StreamingHttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from paas_wl.cnative.specs.models import AppModelRevision, BkAppResource
from paas_wl.cnative.specs.procs import parse_image
from paas_wl.networking.entrance.shim import get_builtin_addr_preferred
from paas_wl.utils.views import IgnoreClientContentNegotiation
from paas_wl.workloads.processes.drf_serializers import (
    NamespaceScopedListWatchRespSLZ,
    WatchEventSLZ,
    WatchProcessesQuerySLZ,
)
from paas_wl.workloads.processes.entities import Instance, Process
from paas_wl.workloads.processes.shim import ProcessManager
from paas_wl.workloads.processes.watch import ProcInstByEnvListWatcher, WatchEvent
from paasng.accessories.iam.permissions.resources.application import AppAction
from paasng.accounts.permissions.application import application_perm_class
from paasng.dev_resources.sourcectl.models import VersionInfo
from paasng.engine.constants import RuntimeType
from paasng.engine.models.deployment import Deployment
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.modules.models import BuildConfig
from paasng.utils.rate_limit.constants import UserAction
from paasng.utils.rate_limit.fixed_window import rate_limits_by_user

logger = logging.getLogger(__name__)


@dataclass
class ModuleScopedData:
    module_name: str
    build_method: RuntimeType
    is_deployed: bool
    exposed_url: Optional[str]
    version_info: Optional[VersionInfo] = None

    processes: List[Process] = field(default_factory=list)
    instances: List[Instance] = field(default_factory=list)
    proc_specs: List[Dict] = field(default_factory=list)

    @property
    def total_available_instance_count(self) -> int:
        return sum(p.status.success for p in self.processes if p.status)

    @property
    def total_desired_replicas(self) -> int:
        # Q: 为什么不使用 process_specs 的 target_replicas
        # A: 因为该字段对自动扩缩容的进程无效
        return sum(p.status.replicas for p in self.processes if p.status)

    @property
    def total_failed(self) -> int:
        return sum(p.status.failed for p in self.processes if p.status)


class ListAndWatchProcsViewSet(GenericViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    # Use special negotiation class to accept "text/event-stream" content type
    content_negotiation_class = IgnoreClientContentNegotiation

    @swagger_auto_schema(response_serializer=NamespaceScopedListWatchRespSLZ)
    def list(self, request, code, environment):
        """获取当前进程与进程实例，支持通过 release_id 参数过滤结果"""
        application = self.get_application()
        module_envs = application.envs.filter(environment=environment)

        grouped_data: Dict[str, ModuleScopedData] = {}
        grouped_proc_specs = {
            module_env.module.name: ProcessManager(module_env).list_processes_specs() for module_env in module_envs
        }
        processes_status = ProcInstByEnvListWatcher(application, environment).list()

        for module_env in module_envs:
            module_name = module_env.module.name
            is_living, addr = get_builtin_addr_preferred(module_env)
            exposed_url = None
            version_info = None
            if is_living and addr:
                exposed_url = addr.url

            build_config = BuildConfig.objects.get_or_create_by_module(module_env.module)
            try:
                deployment = Deployment.objects.filter_by_env(module_env).latest_succeeded()
                if (
                    application.type == ApplicationType.CLOUD_NATIVE
                    and build_config.build_method == RuntimeType.CUSTOM_IMAGE
                ):
                    bkapp_revision = AppModelRevision.objects.get(pk=deployment.bkapp_revision_id)
                    res = BkAppResource(**bkapp_revision.json_value)
                    image_name, image_tag = parse_image(res)
                    version_info = VersionInfo(revision="", version_name=image_tag, version_type="tag")
                else:
                    version_info = deployment.version_info
            except Deployment.DoesNotExist:
                logger.debug("Module: %s Env: %s is not deployed", module_name, environment)

            grouped_data[module_name] = ModuleScopedData(
                module_name=module_name,
                is_deployed=is_living,
                exposed_url=exposed_url,
                build_method=build_config.build_method,
                version_info=version_info,
                proc_specs=grouped_proc_specs.get(module_name) or [],
            )

        for process in processes_status.processes:
            module_name = process.app.module_name
            container = grouped_data[module_name]
            container.processes.append(process)
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
