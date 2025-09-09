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
from os import PathLike
from typing import TYPE_CHECKING, Dict, Optional

from django.conf import settings
from django.utils.translation import gettext as _

from paas_wl.infras.cluster.allocator import ClusterAllocator
from paas_wl.infras.cluster.entities import AllocationContext
from paas_wl.infras.resources.base.base import get_client_by_cluster_name
from paas_wl.infras.resources.kube_res.base import Schedule
from paasng.misc.tools.smart_app.constants import SmartBuildPhaseType
from paasng.misc.tools.smart_app.output import make_channel_stream
from paasng.misc.tools.smart_app.phases_steps import SmartBuildPhaseManager
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.handlers import get_desc_handler
from paasng.platform.engine.constants import JobStatus
from paasng.platform.engine.exceptions import HandleAppDescriptionError
from paasng.platform.smart_app.services.detector import SourcePackageStatReader

from .flow import SmartBuildCoordinator, SmartBuildProcedure, SmartBuildStateMgr
from .handler import ContainerRuntimeSpec, SmartBuilderTemplate, SmartBuildHandler
from .poller import BuildProcessPoller, BuildProcessResultHandler

if TYPE_CHECKING:
    from paasng.misc.tools.smart_app.models import SmartBuildRecord
    from paasng.misc.tools.smart_app.output import SmartBuildStream

logger = logging.getLogger(__name__)


class SmartAppBuilder:
    """The main controller for building a s-mart app package"""

    phase_type: Optional[SmartBuildPhaseType] = None

    def __init__(self, smart_build: "SmartBuildRecord", source_package_url: str, package_path: PathLike):
        self.smart_build = smart_build
        self.source_package_url = source_package_url
        self.package_path = package_path
        self.state_mgr = SmartBuildStateMgr.from_smart_build_id(
            smart_build_id=smart_build.uuid, phase_type=SmartBuildPhaseType.PREPARATION
        )
        self.stream: "SmartBuildStream" = make_channel_stream(smart_build)
        self.coordinator = SmartBuildCoordinator(f"{smart_build.operator}:{smart_build.app_code}")

        self.procedure = partial(SmartBuildProcedure, self.stream, self.smart_build)

    def start(self):
        """Start the s-mart building process"""
        logger.info(f"Starting smart build process for build id: {self.smart_build.uuid}")

        phase_manager = SmartBuildPhaseManager(self.smart_build)
        preparation_phase = phase_manager.get_or_create(SmartBuildPhaseType.PREPARATION)

        # 准备阶段
        start_phase(self.smart_build, self.stream, SmartBuildPhaseType.PREPARATION)
        with self.procedure("校验应用描述文件", phase=preparation_phase):
            self.validate_app_description()

        # TODO: 添加其他在准备阶段执行的步骤
        end_phase(self.smart_build, self.stream, JobStatus.SUCCESSFUL, SmartBuildPhaseType.PREPARATION)

        # 构建阶段
        build_phase = phase_manager.get_or_create(SmartBuildPhaseType.BUILD)
        with self.procedure("启动构建阶段", phase=build_phase):
            self.async_start_build_process()

    def validate_app_description(self):
        """Validate the app description file"""
        # TODO: 添加 app_desc 的检查逻辑
        stat = SourcePackageStatReader(self.package_path).read()
        try:
            app_desc = get_desc_handler(stat.meta_info).app_desc
        except DescriptionValidationError as e:
            raise HandleAppDescriptionError(reason=_("处理应用描述文件失败：{}".format(e)))

        if app_desc.market is None:
            raise HandleAppDescriptionError(reason=_("处理应用描述文件失败"))

    def async_start_build_process(self):
        """Start a new s-mart build process and check status periodically"""
        self.launch_build_process()
        self.state_mgr.update()

        params = {"smart_build_id": self.smart_build.uuid}
        BuildProcessPoller.start(params, BuildProcessResultHandler)

    def launch_build_process(self):
        """Start a new build process for build smart package"""
        source_get_url = self.source_package_url
        # TODO: 需要指定 bkrepo 的 bucket
        dest_put_url = "https://user:pass@example.com/generic/bkpaas/test-samrt/test.tgz"

        envs: Dict[str, str] = {
            "SOURCE_GET_URL": source_get_url,
            "DEST_PUT_URL": dest_put_url,
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

        builder_template = SmartBuilderTemplate(
            name=generate_builder_name(self.smart_build),
            namespace=get_default_builder_namespace(),
            runtime=runtime,
            schedule=schedule,
        )

        SmartBuildHandler(get_client_by_cluster_name(cluster_name)).build_pod(template=builder_template)


def start_phase(smart_build: "SmartBuildRecord", stream: "SmartBuildStream", phase: SmartBuildPhaseType):
    """开始阶段"""
    phase_obj = smart_build.phases.get(type=phase)
    phase_obj.mark_and_write_to_stream(stream, JobStatus.PENDING)


def end_phase(
    smart_build: "SmartBuildRecord", stream: "SmartBuildStream", status: JobStatus, phase: SmartBuildPhaseType
):
    """结束阶段"""
    phase_obj = smart_build.phases.get(type=phase)
    phase_obj.mark_and_write_to_stream(stream, status)

    for step in phase_obj.get_unfinished_steps():
        step.mark_and_write_to_stream(stream, status)


def get_default_cluster_name() -> str:
    """Get the default cluster name to run smart builder pods"""
    return ClusterAllocator(AllocationContext.create_for_build_app()).get_default()


def generate_builder_name(smart_build: "SmartBuildRecord") -> str:
    """Get the s-mart builder name"""
    return f"builder-{smart_build.app_code.replace('_', '0us0')}-{smart_build.operator}"


def get_default_builder_namespace() -> str:
    """Get the namespace of s-mart builder pod"""
    return "smart-app-builder"
