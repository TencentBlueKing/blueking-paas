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
from typing import TYPE_CHECKING, Type

from blue_krill.async_utils.poll_task import CallbackHandler, CallbackResult, TaskPoller
from django.utils.translation import gettext as _

from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.misc.audit.constants import DataType, OperationEnum, OperationTarget, ResultCode
from paasng.misc.audit.utils import add_app_audit_record, update_app_audit_record
from paasng.platform.applications.signals import module_environment_offline_success
from paasng.platform.engine.constants import JobStatus, OperationTypes, ReleaseStatus
from paasng.platform.engine.exceptions import OfflineOperationExistError
from paasng.platform.engine.models import Deployment, OfflineOperation
from paasng.platform.engine.models.operations import ModuleEnvironmentOperations
from paasng.platform.engine.utils.query import DeploymentGetter, OfflineOperationGetter

if TYPE_CHECKING:
    from paasng.platform.applications.models import ModuleEnvironment

logger = logging.getLogger(__name__)


class BaseArchiveManager:
    """Archive a module environment.

    :param env: the module environment to be archived.
    """

    def __init__(self, env: "ModuleEnvironment"):
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
        ModuleEnvironmentOperations.objects.create(
            operator=operator,
            app_environment=offline_operation.app_environment,
            application=offline_operation.app_environment.application,
            operation_type=OperationTypes.OFFLINE.value,
            object_uid=offline_operation.pk,
        )

        # 审计记录
        add_app_audit_record(
            app_code=self.env.application.code,
            user=operator,
            action_id=AppAction.BASIC_DEVELOP,
            operation=OperationEnum.OFFLINE,
            target=OperationTarget.APP,
            module_name=self.env.module.name,
            env=self.env.environment,
            # 仅下发下架操作，未执行成功
            result_code=ResultCode.ONGOING,
            # 仅记录云原生应用操作前 bkapp.yaml 的版本号
            data_type=DataType.BKAPP_REVERSION,
            data_before=deployment.bkapp_revision_id,
            source_object_id=offline_operation.id.hex,
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
            error_detail = "Unable to perform offline: processes were not stopped in given period"
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
            result_code = ResultCode.SUCCESS
        else:
            offline_op.set_failed(error_detail)
            result_code = ResultCode.FAILURE

        module_environment_offline_success.send(
            sender=OfflineOperation, offline_instance=offline_op, environment=offline_op.app_environment.environment
        )
        # 更新审计记录状态
        update_app_audit_record(offline_op.id.hex, result_code)
