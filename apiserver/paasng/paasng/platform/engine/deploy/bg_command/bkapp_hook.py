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

from six import ensure_text

from paas_wl.bk_app.deploy.app_res.controllers import BkAppHookHandler
from paas_wl.infras.resources.base.exceptions import ReadTargetStatusTimeout
from paas_wl.utils.constants import PodPhase
from paasng.platform.engine.constants import JobStatus
from paasng.platform.engine.exceptions import StepNotInPresetListError
from paasng.platform.engine.models import DeployPhaseTypes
from paasng.platform.engine.utils.output import Style
from paasng.platform.engine.workflow import DeployStep

logger = logging.getLogger(__name__)

# Max timeout seconds for waiting the pre-release-hook pod to become ready
# This timeout should be consistent with the default application
# defined at `paas_wl.bk_app.deploy.actions.exec._WAIT_FOR_READINESS_TIMEOUT`
_WAIT_FOR_READINESS_TIMEOUT = 300

# 检查中断的间隔时间
_INTERRUPT_CHECK_INTERVAL = 10


def generate_pre_release_hook_name(bkapp_name: str, deploy_id: int) -> str:
    """获取钩子 pod 名称. 需要和 operator 中的保持一致"""
    return f"pre-rel-{bkapp_name}-{deploy_id}"


class PreReleaseDummyExecutor(DeployStep):
    """
    Dummy executor for BkApp pre-release hook

    用于前端正确渲染"执行部署前置命令"步骤, 同时获取日志
    """

    phase_type = DeployPhaseTypes.RELEASE
    step_name = "执行部署前置命令"

    def start(self, hook_name: str):
        self._mark_step_start()
        status = self._perform(hook_name)
        self._mark_step_stop(status)

    def _mark_step_start(self):
        try:
            step = self.phase.get_step_by_name(self.step_name)
        except StepNotInPresetListError:
            return
        step.mark_and_write_to_stream(self.stream, JobStatus.PENDING)

    def _perform(self, hook_name: str) -> PodPhase:
        self.stream.write_message(Style.Warning("Starting pre-release phase"))

        wl_app = self.engine_app.to_wl_obj()
        handler = BkAppHookHandler(wl_app, hook_name)

        try:
            handler.wait_for_logs_readiness(timeout=_WAIT_FOR_READINESS_TIMEOUT)
        except ReadTargetStatusTimeout as e:
            pod = e.extra_value
            if pod is None:
                self.stream.write_message(
                    Style.Error("Pod is not created normally, please contact the cluster administrator.")
                )
            return PodPhase.FAILED

        try:
            next_check_at = time.monotonic()
            for line in handler.fetch_logs(follow=True):
                interrupted, next_check_at = self._check_release_interrupted(next_check_at)
                if interrupted:
                    self.stream.write_message(Style.Warning("Pre-release interrupted"))
                    return PodPhase.FAILED

                self.stream.write_message(ensure_text(line))
        except Exception:
            logger.exception(f"A critical error happened during fetch logs from hook({hook_name})")
            self.stream.write_message(Style.Error("fetch logs failed"))

        try:
            return handler.wait_hook_finished()
        except ReadTargetStatusTimeout:
            return PodPhase.RUNNING

    def _check_release_interrupted(self, next_check_at: float) -> tuple[bool, float]:
        """检查 Pre-release 是否被中断"""
        if time.monotonic() <= next_check_at:
            return False, next_check_at

        self.deployment.refresh_from_db(fields=["release_int_requested_at"])
        has_release_interrupted = self.deployment.has_requested_int
        next_check_at = time.monotonic() + _INTERRUPT_CHECK_INTERVAL

        return has_release_interrupted, next_check_at

    def _mark_step_stop(self, status: PodPhase):
        # wait_for_logs_readiness 超时等路径不会经过日志循环的刷新, 需要手动刷新
        self.deployment.refresh_from_db(fields=["release_int_requested_at"])
        is_interrupted = status == PodPhase.FAILED and self.deployment.has_requested_int

        if status == PodPhase.SUCCEEDED:
            self.stream.write_message(Style.Warning("Pre-release execution succeed"))
        elif is_interrupted:
            self.stream.write_message(Style.Warning("Pre-release interrupted"))
        elif status == PodPhase.FAILED:
            self.stream.write_message(Style.Error("Pre-release failed, please check logs for more details"))
        else:
            self.stream.write_message(Style.Warning("Pre-release exceeded timeout"))

        try:
            step = self.phase.get_step_by_name(self.step_name)
        except StepNotInPresetListError:
            return

        if status == PodPhase.SUCCEEDED:
            step.mark_and_write_to_stream(self.stream, JobStatus.SUCCESSFUL)
            return
        if is_interrupted:
            step.mark_and_write_to_stream(self.stream, JobStatus.INTERRUPTED, {"message": "Pre-release interrupted"})
            return
        if status == PodPhase.FAILED:
            step.mark_and_write_to_stream(self.stream, JobStatus.FAILED)
