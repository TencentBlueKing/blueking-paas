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
from typing import TYPE_CHECKING, Type

from blue_krill.async_utils.poll_task import CallbackHandler, CallbackResult, TaskPoller
from django.utils.translation import gettext as _

from paasng.platform.engine.constants import JobStatus, ReleaseStatus
from paasng.platform.engine.exceptions import OfflineOperationExistError
from paasng.platform.engine.models import Deployment, OfflineOperation
from paasng.platform.engine.utils.query import DeploymentGetter, OfflineOperationGetter
from paasng.platform.applications.signals import module_environment_offline_event, module_environment_offline_success

if TYPE_CHECKING:
    from paasng.platform.applications.models import ModuleEnvironment

logger = logging.getLogger(__name__)


class BaseArchiveManager:
    """Archive a module environment.

    :param env: the module environment to be archived.
    """

    def __init__(self, env: 'ModuleEnvironment'):
        self.env = env

    def perform_env_offline(self, operator: str) -> OfflineOperation:
        """执行下架 env, 如果环境已下架, 则直接返回

        :param operator: 操作人(user_id)
        :return: OfflineOperation
        :raise Deployment.DoseNotExist: 未曾部署成功, 无需下架
        :raise OfflineOperationExistError: 当已存在正在下架的任务时抛该异常
        """
        deployment = DeploymentGetter(env=self.env).get_latest_succeeded()
        if deployment is None:
            # raise Deployment.DoseNotExist 即说明没有成功部署，那么也不存在下架的必要
            raise Deployment.DoesNotExist
        latest_offline_operation = OfflineOperationGetter(env=self.env).get_latest_succeeded()
        if latest_offline_operation is not None:
            return latest_offline_operation

        current_operation = OfflineOperationGetter(env=self.env).get_current_operation()
        if current_operation is not None:
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

        self.perform_implement(offline_operation, result_handler=ArchiveResultHandler)
        return offline_operation

    def perform_implement(self, offline_operation: OfflineOperation, result_handler: Type[CallbackHandler]):
        """Start the offline operation, this will start background task, and call result handler when task finished"""
        raise NotImplementedError


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
