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
import time
from contextlib import contextmanager
from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Tuple

from blue_krill.data_types.enum import EnumField, StrStructuredEnum
from django.utils.translation import gettext as _

from paas_wl.infras.resources.base.base import get_all_cluster_names
from paas_wl.infras.resources.kube_res.base import Schedule
from paas_wl.utils.constants import BuildStatus, PodPhase
from paasng.misc.tools.build_smart.models import SmartBuildRecord, SourceCodeOriginType
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.handlers import get_desc_handler
from paasng.platform.smart_app.services.detector import SourcePackageStatReader

from .coordinator import SmartBuildCoordinator
from .exceptions import SmartBuildError, SmartBuildInterruptionFailed, SmartBuildStepError
from .output import get_default_stream
from .pod import Containers, SmartBuildRunner, SmartBuildSpec

logger = logging.getLogger(__name__)


class BuildPhaseTypes(StrStructuredEnum):
    """构建阶段"""

    PREPARATION = EnumField("preparation", label=_("准备阶段"))
    BUILD = EnumField("build", label=_("构建阶段"))


class BuildStep(Protocol):
    """构建步骤协议"""

    def __call__(self) -> None: ...


@dataclass
class BuildPhase:
    """构建阶段配置"""

    name: str
    steps: List[Tuple[str, BuildStep]]


def initialize_smart_build_record(
    package_path: PathLike,
    signature: str,
    operator: str,
) -> SmartBuildRecord:
    """Initialize s-smart package build record

    :param package_path: Path to the source package file
    :param signature: SHA256 hash of the source package
    :param operator: The user ID of the operator
    """

    # TODO: Support source code repository locally and obtaining the branch
    source_origin = SourceCodeOriginType.PACKAGE.value
    branch = ""
    package_name = Path(package_path).name
    status = BuildStatus.PENDING.value

    record = SmartBuildRecord.objects.create(
        source_origin=source_origin,
        branch=branch,
        package_name=package_name,
        signature=signature,
        status=status,
        operator=operator,
    )
    record.refresh_from_db()
    return record


class SmartBuildTaskRunner:
    """Start a s-mart build task

    Coordinate the build process, including verification, building, and launching
    """

    def __init__(self, smart_build: SmartBuildRecord, source_package_path: PathLike):
        self.smart_build = smart_build
        # TODO: 这里是本地地址, 之后应该将其上传到云端存储?
        self.source_package_path = source_package_path
        self.start_time = time.time()
        self.writer = get_default_stream(smart_build)
        self.coordinator = SmartBuildCoordinator(self.smart_build.signature)

        self.artifact_url: Optional[str] = ""
        self.spec: Optional[SmartBuildSpec] = None

        self.phases: List[BuildPhase] = [
            BuildPhase(
                name=BuildPhaseTypes.PREPARATION.value,
                steps=[
                    ("validate_app_desc", self._validate_app_desc),
                    ("verify_file_dir", self._verify_file_dir),
                    ("scan_sensitive_information", self._scan_sensitive_information),
                ],
            ),
            BuildPhase(
                name=BuildPhaseTypes.BUILD.value,
                steps=[
                    ("init_build_spec", self._init_build_spec),
                    ("run_smart_build_process", self._run_smart_build_process),
                ],
            ),
        ]

    def start(self):
        """Start a s-mart build task"""

        self.update_smart_build_status(BuildStatus.PENDING.value)

        try:
            self._execute_phases()
            self.update_smart_build_status(BuildStatus.SUCCESSFUL)
        except SmartBuildInterruptionFailed:
            logger.info("Smart build interrupted by user")
            self.update_smart_build_status(BuildStatus.INTERRUPTED)
        except SmartBuildError:
            logger.exception("Smart build task failed")
            self.update_smart_build_status(BuildStatus.FAILED)
        finally:
            # Close writer stream
            self.writer.close()

    def update_smart_build_status(self, status: BuildStatus):
        """Update s-mart build record"""
        if status == BuildStatus.SUCCESSFUL and self.artifact_url:
            self.smart_build.artifact_url = self.artifact_url

        self.smart_build.status = status
        if status in BuildStatus.get_finished_states():
            self.smart_build.time_spent = int(time.time() - self.start_time)
        self.smart_build.save(update_fields=["status", "time_spent", "artifact_url"])

    def _execute_phases(self):
        """Execute phases and steps; centralizes phase/step event handling."""
        for build_phase in self.phases:
            self.writer.write_event("phase", {"name": build_phase.name, "status": "started"})
            try:
                for step_name, step_fn in build_phase.steps:
                    self.coordinator.update_polling_time()
                    self._check_interrupted()
                    with self._step_context(step_name):
                        step_fn()
            except SmartBuildInterruptionFailed:
                self.writer.write_event("phase", {"name": build_phase.name, "status": "interruption"})
                raise
            except SmartBuildStepError:
                # step or phase failed -> emit failed and re-raise for outer handler
                self.writer.write_event("phase", {"name": build_phase.name, "status": "failed"})
                raise SmartBuildError(f"Phase '{build_phase.name}' failed during execution")

            self.writer.write_event("phase", {"name": build_phase.name, "status": "completed"})

    def _check_interrupted(self):
        """Ensure the build process has not been interrupted by user"""
        if self.coordinator.get_interrupted_time():
            raise SmartBuildInterruptionFailed(_("用户已经发送构建中断请求"))

    @contextmanager
    def _step_context(self, name: str):
        """Context manager to emit step events: started -> (completed|failed)."""
        self.writer.write_event("step", {"name": name, "status": "started"})
        try:
            yield
        except Exception:
            self.writer.write_event("step", {"name": name, "status": "failed"})
            raise SmartBuildStepError(f"Step '{name}' failed during execution")
        else:
            self.writer.write_event("step", {"name": name, "status": "completed"})

    # --- step implementations (keep as small focused methods) ---

    def _validate_app_desc(self):
        """Validate app_desc file"""
        # TODO: 构建 s-mart 包时, 准备阶段的 app_desc 文件检查
        stat = SourcePackageStatReader(self.source_package_path).read()
        app_desc = get_desc_handler(stat.meta_info).app_desc
        if app_desc.market is None:
            raise DescriptionValidationError({"market": "内容不能为空"})

    def _verify_file_dir(self):
        """Verify the source package file directory"""
        # TODO: 检查应用源码中的文件和目录结构
        logger.info("验证源码包文件目录结构")

    def _scan_sensitive_information(self):
        """Scan sensitive information, Only the cloud version is checked

        Need to call codecc API
        """
        # TODO: 扫描应用源码中的敏感信息, 只有上云版才需要检查
        logger.info("上云版扫描敏感信息")

    def _init_build_spec(self):
        """Build SmartBuildSpec object"""
        # TODO: 后面需要动态获取这个参数, 最后的文件名应该是 app_code.tgz
        source_get_url = "https://username:password@example.com/generic/bkpaas/test-smart/hello.tar.gz"
        dest_put_url = "https://username:password@example.com/generic/bkpaas/test-smart/smart-test-proj.tgz"

        envs: Dict[str, str] = {
            "SOURCE_GET_URL": source_get_url,
            "DEST_PUT_URL": dest_put_url,
            "BUILDER_SHIM_IMAGE": "mirrors.tencent.com/bkpaas/bk-builder-heroku-bionic:v1.2.0",
        }

        # Use first useful cluster name as default
        clusters = get_all_cluster_names()
        cluster_name = clusters[0]

        # TODO: 执行镜像应该也需要判断一下是使用 dind 还是 pind
        self.spec = SmartBuildSpec(
            containers=Containers(
                image="mirrors.tencent.com/bkpaas/smart-app-builder:dind",
                envs=envs,
            ),
            schedule=Schedule(
                cluster_name=cluster_name,
                tolerations=[],
                node_selector={},
            ),
        )

        self.artifact_url = dest_put_url

    def _run_smart_build_process(self):
        """Building the s-mart package in k8s"""

        if not self.spec:
            raise SmartBuildStepError("SmartBuildSpec is not initialized, cannot run build process")
        final_status = SmartBuildRunner(smart_build=self.smart_build, spec=self.spec).start()

        if final_status == PodPhase.FAILED:
            raise SmartBuildStepError(f"Build failed with Pod status: {final_status}")
