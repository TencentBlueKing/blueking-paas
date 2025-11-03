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

import logging
from functools import partial
from typing import TYPE_CHECKING, Dict

from django.conf import settings
from django.utils.encoding import force_str

from paas_wl.bk_app.deploy.app_res.controllers import NamespacesHandler
from paas_wl.infras.cluster.allocator import ClusterAllocator
from paas_wl.infras.cluster.entities import AllocationContext
from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paas_wl.infras.resources.kube_res.base import Schedule
from paasng.misc.tools.smart_app.constants import SmartBuildPhaseType
from paasng.misc.tools.smart_app.output import make_channel_stream
from paasng.platform.engine.constants import JobStatus

from .flow import SmartBuildProcedure, SmartBuildStateMgr
from .handler import ContainerRuntimeSpec, SmartBuilderTemplate, SmartBuildHandler
from .poller import SmartBuildProcessPoller, SmartBuildProcessResultHandler

if TYPE_CHECKING:
    from paasng.misc.tools.smart_app.models import SmartBuildPhase, SmartBuildRecord
    from paasng.misc.tools.smart_app.output import SmartBuildStream

logger = logging.getLogger(__name__)


class SmartAppBuilder:
    """The main controller for building a s-mart app package"""

    phase_type: SmartBuildPhaseType | None = None

    def __init__(
        self,
        smart_build: "SmartBuildRecord",
        source_get_url: str,
        dest_put_url: str,
    ):
        self.smart_build = smart_build
        self.source_get_url = source_get_url
        self.dest_put_url = dest_put_url

        self.stream: "SmartBuildStream" = make_channel_stream(smart_build)
        self.state_mgr = SmartBuildStateMgr.from_smart_build_id(smart_build.uuid, self.stream)
        self.procedure = partial(SmartBuildProcedure, self.stream, self.smart_build)

    def start(self):
        """Start the s-mart building process"""

        try:
            # 开始准备阶段
            start_phase(self.smart_build, self.stream, SmartBuildPhaseType.PREPARATION)
            preparation_phase = self.smart_build.phases.get(type=SmartBuildPhaseType.PREPARATION)

            with self.procedure("校验应用描述文件", phase=preparation_phase):
                self.validate_app_description()

            # 结束准备阶段
            end_phase(self.smart_build, self.stream, JobStatus.SUCCESSFUL, SmartBuildPhaseType.PREPARATION)

            # 开始构建阶段
            start_phase(self.smart_build, self.stream, SmartBuildPhaseType.BUILD)
            build_phase = self.smart_build.phases.get(type=SmartBuildPhaseType.BUILD)

            self._start_build_process(build_phase)

            # 结束构建阶段
            end_phase(self.smart_build, self.stream, JobStatus.SUCCESSFUL, SmartBuildPhaseType.BUILD)

        finally:
            self._finish_builder()

    def _start_build_process(self, build_phase: "SmartBuildPhase"):
        """启动构建流程"""

        with self.procedure("准备构建环境", phase=build_phase):
            builder_name = self.launch_build_process()

        with self.procedure("构建 S-Mart 包", phase=build_phase):
            self.start_following_logs(builder_name)

            params = {"smart_build_id": self.smart_build.uuid}

        SmartBuildProcessPoller.start(params, SmartBuildProcessResultHandler)

    def _finish_builder(self):
        """结束整体的构建流程"""

        self.stream.close()

        self.state_mgr.coordinator.release_lock(self.smart_build)

    def validate_app_description(self):
        """Validate the app description file"""

        # TODO: 添加 app_desc 的检查逻辑

    def start_following_logs(self, builder_name: str):
        """获取并流式输出构建日志,并检查 Pod 执行状态"""

        namespace = get_default_builder_namespace()
        cluster_name = get_default_cluster_name()
        handler = SmartBuildHandler(get_client_by_cluster_name(cluster_name))

        handler.wait_for_logs_readiness(namespace, builder_name, settings.SMART_BUILD_PROCESS_TIMEOUT)

        for raw_line in handler.get_build_log(
            namespace=namespace, name=builder_name, follow=True, timeout=settings.SMART_BUILD_PROCESS_TIMEOUT
        ):
            self.stream.write_message(force_str(raw_line))

        handler.wait_for_succeeded(namespace=namespace, name=builder_name, timeout=60)

        self.smart_build.update_fields(status=JobStatus.SUCCESSFUL)

    def launch_build_process(self) -> str:
        """launch the build Pod and return the Pod name"""

        envs: Dict[str, str] = {
            "SOURCE_GET_URL": self.source_get_url,
            "DEST_PUT_URL": self.dest_put_url,
            "BUILDER_SHIM_IMAGE": settings.SMART_BUILDER_SHIM_IMAGE,
        }

        cluster_name = get_default_cluster_name()

        runtime = ContainerRuntimeSpec(
            image=settings.SMART_BUILDER_IMAGE,
            envs=envs,
        )

        schedule = Schedule(
            cluster_name=cluster_name,
            tolerations=[],
            node_selector={},
        )

        namespace = get_default_builder_namespace()
        pod_name = generate_builder_name(self.smart_build)

        client = get_client_by_cluster_name(cluster_name)
        NamespacesHandler(client).ensure_namespace(namespace)

        builder_template = SmartBuilderTemplate(
            name=pod_name,
            namespace=namespace,
            runtime=runtime,
            schedule=schedule,
        )

        smart_build_handler = SmartBuildHandler(client)
        return smart_build_handler.build_pod(template=builder_template)


def start_phase(smart_build: "SmartBuildRecord", stream: "SmartBuildStream", phase: SmartBuildPhaseType):
    """开始阶段"""

    phase_obj: "SmartBuildPhase" = smart_build.phases.get(type=phase)
    phase_obj.mark_and_write_to_stream(stream, JobStatus.PENDING)


def end_phase(
    smart_build: "SmartBuildRecord", stream: "SmartBuildStream", status: JobStatus, phase: SmartBuildPhaseType
):
    """结束阶段"""

    phase_obj: "SmartBuildPhase" = smart_build.phases.get(type=phase)
    phase_obj.mark_and_write_to_stream(stream, status)

    for step in phase_obj.get_unfinished_steps():
        step.mark_and_write_to_stream(stream, status)


def get_default_cluster_name() -> str:
    """Get the default cluster name to run smart builder pods"""

    cluster = ClusterAllocator(AllocationContext.create_for_build_app()).get_default()
    return cluster.name


def generate_builder_name(smart_build: "SmartBuildRecord") -> str:
    """Get the s-mart builder name"""

    return f"builder-{smart_build.app_code.replace('_', '0us0')}-{smart_build.operator}"


def get_default_builder_namespace() -> str:
    """Get the namespace of s-mart builder pod"""

    return "smart-app-builder"
