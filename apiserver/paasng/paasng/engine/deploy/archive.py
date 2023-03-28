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
import logging
from typing import TYPE_CHECKING, Optional, Tuple

from blue_krill.async_utils.poll_task import CallbackHandler, CallbackResult, TaskPoller
from django.conf import settings
from django.utils.translation import gettext as _

from paas_wl.resources.actions.archive import ArchiveOperationController
from paasng.engine.constants import JobStatus, ReleaseStatus
from paasng.engine.exceptions import OfflineOperationExistError
from paasng.engine.models.deployment import Deployment
from paasng.engine.models.offline import OfflineOperation
from paasng.engine.processes.wait import wait_for_all_stopped
from paasng.platform.applications.signals import module_environment_offline_event, module_environment_offline_success

if TYPE_CHECKING:
    from paasng.platform.applications.models import ModuleEnvironment

logger = logging.getLogger(__name__)


class OfflineManager:
    """Archive a module environment.

    :param env: the module environment to be archived.
    """

    def __init__(self, env: 'ModuleEnvironment'):
        self.env = env

    def has_been_offline(self, latest_deployment: Deployment) -> Tuple[Optional[OfflineOperation], bool]:
        """是否处于下架状态，是则同时返回最近一次的 OfflineOperation"""
        try:
            latest_offline_operation = OfflineOperation.objects.filter(app_environment=self.env).latest_succeeded()
        except OfflineOperation.DoesNotExist:
            pass
        else:
            # 如果存在已下架成功记录，并且比最近一次部署成功记录更新，说明应用已经是下架过了，则不再重复下架
            if latest_offline_operation.created > latest_deployment.created:
                logger.info("the module has been offline, just skip")
                return latest_offline_operation, True

        return None, False

    def get_latest_succeeded_deployment(self):
        return Deployment.objects.filter_by_env(env=self.env).latest_succeeded()

    def perform_env_offline(self, operator: str):
        """可重入的下架操作，返回 OfflineOperation"""
        # raise DoseNotExist 即说明没有成功部署，那么也不存在下架的必要
        deployment = self.get_latest_succeeded_deployment()
        latest_offline_operation, has_been_offline = self.has_been_offline(deployment)
        if has_been_offline:
            return latest_offline_operation

        try:
            OfflineOperation.objects.filter(app_environment=self.env).get_latest_resumable(
                max_resumable_seconds=settings.ENGINE_OFFLINE_RESUMABLE_SECS
            )
        except OfflineOperation.DoesNotExist:
            pass
        else:
            # 存在正在下架操作，不再重复发起
            raise OfflineOperationExistError(_("存在正在进行的下架任务"))

        offline_operation = OfflineOperation.objects.create(
            operator=operator,
            app_environment=self.env,
            source_type=deployment.source_type,
            source_location=deployment.source_location,
            source_version_type=deployment.source_version_type,
            source_version_name=deployment.source_version_name,
            source_revision=deployment.source_revision,
            source_comment=deployment.source_comment,
        )

        # send offline event to create operation record
        module_environment_offline_event.send(
            sender=offline_operation, offline_instance=offline_operation, environment=self.env.environment
        )

        # Start the offline operation, this will start background task
        op_id = str(offline_operation.pk)
        ArchiveOperationController(env=self.env, operation_id=op_id).start()
        wait_for_all_stopped(env=self.env, result_handler=ArchiveResultHandler, extra_params={"operation_id": op_id})
        return offline_operation


class ArchiveResultHandler(CallbackHandler):
    """Handler for archive operation"""

    def handle(self, result: CallbackResult, poller: TaskPoller):
        if result.is_exception:
            error_detail = 'Unable to perform offline: processes were not stopped in given period'
            status = ReleaseStatus.FAILED
        else:
            error_detail = ""
            status = ReleaseStatus.SUCCESSFUL

        operation_id = poller.params["extra_params"]["operation_id"]
        self.finish_archive(operation_id, status, error_detail)

    def finish_archive(self, operation_id: str, status: ReleaseStatus, error_detail: str):
        """Finish archive operation"""
        offline_op = OfflineOperation.objects.get(id=operation_id)
        job_status = status.to_job_status()
        if job_status == JobStatus.SUCCESSFUL:
            offline_op.set_successful()
        else:
            offline_op.set_failed(error_detail)

        module_environment_offline_success.send(
            sender=OfflineOperation, offline_instance=offline_op, environment=offline_op.app_environment.environment
        )
