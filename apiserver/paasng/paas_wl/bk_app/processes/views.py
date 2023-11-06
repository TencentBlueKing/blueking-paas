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
from operator import attrgetter
from typing import Dict, Optional

from django.http import StreamingHttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from paas_wl.bk_app.processes.drf_serializers import (
    ModuleScopedData,
    ModuleState,
    NamespaceScopedListWatchRespSLZ,
    OperationGroup,
    WatchEventSLZ,
    WatchProcessesQuerySLZ,
)
from paas_wl.bk_app.processes.shim import ProcessManager
from paas_wl.bk_app.processes.watch import ProcInstByEnvListWatcher, WatchEvent
from paas_wl.utils.views import IgnoreClientContentNegotiation
from paas_wl.workloads.networking.entrance.shim import get_builtin_addr_preferred
from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin
from paasng.platform.bkapp_model.utils import get_image_info
from paasng.platform.engine.constants import RuntimeType
from paasng.platform.engine.deploy.version import get_env_deployed_version_info
from paasng.platform.engine.utils.query import DeploymentGetter, OfflineOperationGetter
from paasng.platform.modules.models import Module
from paasng.utils.rate_limit.constants import UserAction
from paasng.utils.rate_limit.fixed_window import rate_limits_by_user

logger = logging.getLogger(__name__)


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
            try:
                return get_image_info(module)[0]
            except ValueError:
                return None
        repo = module.get_source_obj()
        if repo is None:
            return None
        return repo.get_repo_url()
