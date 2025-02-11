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

from bkpaas_auth.models import User
from django.utils import timezone
from django.utils.translation import gettext as _

from paasng.platform.engine.constants import JobStatus
from paasng.platform.engine.deploy.bg_build.bg_build import interrupt_build_proc
from paasng.platform.engine.exceptions import DeployInterruptionFailed
from paasng.platform.engine.models.deployment import Deployment
from paasng.platform.engine.workflow import DeploymentCoordinator

logger = logging.getLogger(__name__)


def interrupt_deployment(deployment: Deployment, user: User):
    """Interrupt a deployment, this method does not guarantee that the deployment will be interrupted
    immediately(or in a few seconds). It will try to do following things:

    - When in "build" phase: this method will try to stop the build process by calling engine service
    - When in "release" phase: this method will set a flag value and abort the polling process of
      current release

    After finished doing above things, the deployment process MIGHT be stopped if anything goes OK, while
    the interruption may have no effects at all if the deployment was not in the right status.

    :param deployment: Deployment object to interrupt
    :param user: User who invoked interruption
    :raises: DeployInterruptionFailed
    """
    if deployment.operator != user.pk:
        raise DeployInterruptionFailed(_("无法中断由他人发起的部署"))
    if deployment.status in JobStatus.get_finished_states():
        raise DeployInterruptionFailed(_("无法中断，部署已处于结束状态"))

    now = timezone.now()
    deployment.build_int_requested_at = now
    deployment.release_int_requested_at = now
    deployment.save(update_fields=["build_int_requested_at", "release_int_requested_at", "updated"])

    # 若部署进程的数据上报已经超时，则认为部署失败，主动解锁
    coordinator = DeploymentCoordinator(deployment.app_environment)
    coordinator.release_if_polling_timed_out(expected_deployment=deployment)

    if deployment.build_process_id:
        try:
            interrupt_build_proc(deployment.build_process_id)
        except DeployInterruptionFailed:
            # This exception means that build has not been started yet, transform
            # the error message.
            raise DeployInterruptionFailed("任务正处于预备执行状态，无法中断，请稍候重试")
