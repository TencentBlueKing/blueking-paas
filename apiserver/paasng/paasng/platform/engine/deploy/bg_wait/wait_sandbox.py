# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

"""Wait for SandboxInstance CR to be ready.

AI Agent 应用的工作负载由 SandboxInstance CR 承载, 与 BkApp CR 不同, 它没有
status.conditions / status.deployId 等字段, 只有 status.phase。因此需要独立的 poller
读取 phase 判断就绪, 并复用 DeployStatusHandler 把结果回填到 AppModelDeploy.status。
"""

import logging
from typing import List

from blue_krill.async_utils.poll_task import PollingResult

from paas_wl.bk_app.cnative.specs.constants import DeployStatus
from paas_wl.bk_app.cnative.specs.models import AppModelDeploy
from paas_wl.bk_app.cnative.specs.resource import ModelResState
from paas_wl.bk_app.sandbox_instance.constants import SandboxInstancePhase
from paas_wl.bk_app.sandbox_instance.exceptions import SandboxInstanceNotFound
from paas_wl.bk_app.sandbox_instance.resource import SandboxInstanceManager
from paas_wl.core.resource import generate_bkapp_name
from paas_wl.infras.cluster.shim import EnvClusterService
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.deploy.bg_wait.wait_bkapp import (
    AbortPolicy,
    UserInterruptedPolicy,
    WaitBkAppProcedurePoller,
    update_status,
)

logger = logging.getLogger(__name__)


class WaitSandboxInstanceReady(WaitBkAppProcedurePoller):
    """轮询 SandboxInstance CR 的 status.phase, 判定发布是否就绪。

    `params` schema:
    :param env_id: id of ModuleEnvironment object
    :param deploy_id: int, ID of AppModelDeploy object
    :param deployment_id: Optional[uuid]: ID of Deployment object
    """

    # over 15 min considered as timeout
    overall_timeout_seconds = 15 * 60
    abort_policies: List[AbortPolicy] = [UserInterruptedPolicy()]

    def get_status(self) -> PollingResult:
        deploy_id = self.params["deploy_id"]
        dp = AppModelDeploy.objects.get(id=deploy_id)
        env = ModuleEnvironment.objects.get(
            application_id=dp.application_id, module_id=dp.module_id, environment=dp.environment_name
        )

        cluster_name = EnvClusterService(env).get_cluster_name()
        wl_app = env.wl_app
        try:
            obj = SandboxInstanceManager(cluster_name).get(wl_app.namespace, generate_bkapp_name(env))
        except SandboxInstanceNotFound:
            # CR 尚未被 apiserver 记录, 继续等待
            return PollingResult.doing()

        status = obj.get("status", {}) or {}
        phase = status.get("phase")
        message = status.get("message", "")

        if phase == SandboxInstancePhase.RUNNING.value:
            state = ModelResState(DeployStatus.READY, "Running", message or "SandboxInstance is running")
            return PollingResult.done(data={"state": state, "last_update": None})

        if phase == SandboxInstancePhase.FAILED.value:
            state = ModelResState(DeployStatus.ERROR, "Failed", message or "SandboxInstance failed")
            return PollingResult.done(data={"state": state, "last_update": None})

        # Pending / Creating / Stopping 等中间态: 把进展写回 AppModelDeploy(status=PROGRESSING),
        # 使部署历史能实时反映"部署中"及最新 message, 与 WaitAppModelReady 对 PROGRESSING 的处理对齐。
        # (超时 / 用户中断由 poll_task 触发, 经 DeployStatusHandler 统一落到 ERROR / UNKNOWN, 无需在此处理)
        state = ModelResState(
            DeployStatus.PROGRESSING, phase or "Progressing", message or f"SandboxInstance phase: {phase}"
        )
        update_status(dp, state)
        return PollingResult.doing(data={"phase": phase})
