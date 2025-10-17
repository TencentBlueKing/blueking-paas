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
from typing import TYPE_CHECKING, Dict, Optional

from django.conf import settings
from django.utils.encoding import force_str

from paas_wl.infras.cluster.allocator import ClusterAllocator
from paas_wl.infras.cluster.entities import AllocationContext
from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paas_wl.infras.resources.kube_res.base import Schedule
from paasng.misc.tools.smart_app.build_phase import get_phase
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

    phase_type: Optional[SmartBuildPhaseType] = None

    def __init__(self, smart_build: "SmartBuildRecord", source_get_url: str, dest_put_url: str):
        self.smart_build = smart_build
        self.source_get_url = source_get_url
        self.dest_put_url = dest_put_url

        self.state_mgr = SmartBuildStateMgr.from_smart_build_id(
            smart_build_id=smart_build.uuid, phase_type=SmartBuildPhaseType.PREPARATION
        )
        self.stream: "SmartBuildStream" = make_channel_stream(smart_build)
        self.procedure = partial(SmartBuildProcedure, self.stream, self.smart_build)

    def start(self):
        """Start the s-mart building process"""
        final_status = JobStatus.PENDING
        try:
            self._run_preparation_phase()
            self._run_build_phase()
            final_status = JobStatus.SUCCESSFUL
        except Exception:
            final_status = JobStatus.FAILED
        finally:
            self._finalize_stream(final_status)
            self.state_mgr.finish(final_status)

    def _run_preparation_phase(self):
        """执行准备阶段"""
        preparation_phase = get_phase(self.smart_build, SmartBuildPhaseType.PREPARATION)
        start_phase(self.smart_build, self.stream, SmartBuildPhaseType.PREPARATION)

        try:
            with self.procedure("校验应用描述文件", phase=preparation_phase):
                self.validate_app_description()
            end_phase(self.smart_build, self.stream, JobStatus.SUCCESSFUL, SmartBuildPhaseType.PREPARATION)
        except Exception:
            end_phase(self.smart_build, self.stream, JobStatus.FAILED, SmartBuildPhaseType.PREPARATION)
            raise

    def _run_build_phase(self):
        """执行构建阶段"""
        build_phase = get_phase(self.smart_build, SmartBuildPhaseType.BUILD)
        start_phase(self.smart_build, self.stream, SmartBuildPhaseType.BUILD)

        try:
            with self.procedure("构建 S-Mart 包", phase=build_phase):
                builder_name = self.launch_build_process()

            self.start_following_logs(builder_name)

            params = {"smart_build_id": self.smart_build.uuid, "dest_put_url": self.dest_put_url}
            SmartBuildProcessPoller.start(params, SmartBuildProcessResultHandler)
            end_phase(self.smart_build, self.stream, JobStatus.SUCCESSFUL, SmartBuildPhaseType.BUILD)
        except Exception:
            end_phase(self.smart_build, self.stream, JobStatus.FAILED, SmartBuildPhaseType.BUILD)
            raise

    def _finalize_stream(self, final_status: JobStatus):
        """发送 EOF 事件并关闭 stream"""
        self.stream.write_event("EOF", {"build_id": str(self.smart_build.uuid), "final_status": final_status.value})
        self.stream.close()

    def validate_app_description(self):
        """Validate the app description file"""
        # TODO: 添加对应用描述文件的实际验证逻辑

    def start_following_logs(self, builder_name: str):
        """获取并流式输出构建日志,并检查 Pod 执行状态"""
        namespace = get_default_builder_namespace()
        cluster_name = get_default_cluster_name()
        build_handler = SmartBuildHandler(get_client_by_cluster_name(cluster_name))

        build_handler.wait_for_logs_readiness(
            namespace=namespace, name=builder_name, timeout=settings.SMART_BUILD_PROCESS_TIMEOUT
        )

        for raw_line in build_handler.get_build_log(
            namespace=namespace, name=builder_name, follow=True, timeout=settings.SMART_BUILD_PROCESS_TIMEOUT
        ):
            self.stream.write_message(force_str(raw_line))

        build_handler.wait_for_succeeded(namespace=namespace, name=builder_name, timeout=60)

    def launch_build_process(self) -> str:
        """launch the build Pod"""
        envs: Dict[str, str] = {
            "SOURCE_GET_URL": self.source_get_url,
            "DEST_PUT_URL": self.dest_put_url,
            "BUILDER_SHIM_IMAGE": settings.SMART_BUILDER_SHIM_IMAGE,
        }

        cluster_name = get_default_cluster_name()
        namespace = get_default_builder_namespace()
        pod_name = generate_builder_name(self.smart_build)

        builder_template = SmartBuilderTemplate(
            name=pod_name,
            namespace=namespace,
            runtime=ContainerRuntimeSpec(image=settings.SMART_BUILDER_IMAGE, envs=envs),
            schedule=Schedule(cluster_name=cluster_name, tolerations=[], node_selector={}),
        )

        smart_build_handler = SmartBuildHandler(get_client_by_cluster_name(cluster_name))
        return smart_build_handler.build_pod(template=builder_template)


def start_phase(smart_build: "SmartBuildRecord", stream: "SmartBuildStream", phase: SmartBuildPhaseType):
    phase_obj: "SmartBuildPhase" = smart_build.phases.get(type=phase.value)
    phase_obj.mark_and_write_to_stream(stream, JobStatus.PENDING)


def end_phase(
    smart_build: "SmartBuildRecord", stream: "SmartBuildStream", status: JobStatus, phase: SmartBuildPhaseType
):
    phase_obj: "SmartBuildPhase" = smart_build.phases.get(type=phase.value)
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
