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
"""Releasing process of an application deployment
"""
import logging
import typing
from typing import Optional

from blue_krill.async_utils.poll_task import CallbackHandler, CallbackResult, CallbackStatus, TaskPoller
from pydantic import ValidationError as DanticValidationError

from paas_wl.platform.external.client import get_plat_client
from paas_wl.release_controller.process.wait import AbortedDetails
from paas_wl.utils.constants import CommandStatus as ReleaseStatus

logger = logging.getLogger(__name__)


def finish_release(deployment_id: str, status: ReleaseStatus, error_detail: str):
    """Callback to API Server"""
    get_plat_client().finish_release(deployment_id, status, error_detail)


class ReleaseResultHandler(CallbackHandler):
    """Result handler for `wait_for_release`"""

    def handle(self, result: CallbackResult, poller: TaskPoller):
        is_interrupted, error_detail = self.get_error_detail(result)
        # Transform release_status
        if is_interrupted:
            status = ReleaseStatus.INTERRUPTED
        elif error_detail:
            status = ReleaseStatus.FAILED
        else:
            status = ReleaseStatus.SUCCESSFUL

        finish_release(
            deployment_id=poller.params['extra_params']['deployment_id'],
            status=status,
            error_detail=error_detail,
        )

    def get_error_detail(self, result: CallbackResult) -> typing.Tuple[bool, str]:
        """Get detailed error message. if error message was empty, release was considered succeeded

        :returns: (is_interrupted, error_msg)
        """
        if result.status == CallbackStatus.TIMEOUT:
            return False, "Timeout: polling release's status taking too long to complete"

        if result.status == CallbackStatus.NORMAL:
            aborted_details = self.get_aborted_details(result)
            if not (aborted_details and aborted_details.aborted):
                return False, ''

            assert aborted_details.policy is not None, 'policy must not be None'  # Make type checker happy
            reason = aborted_details.policy.reason
            return aborted_details.policy.is_interrupted, f'Release aborted, reason: {reason}'

        return False, 'Release failed, internal error'

    def get_aborted_details(self, result: CallbackResult) -> Optional[AbortedDetails]:
        """If current release was aborted, return detailed info"""
        try:
            details = AbortedDetails.parse_obj(result.data)
        except DanticValidationError:
            return None
        return details


def finish_archive(operation_id: str, status: ReleaseStatus, error_detail: str):
    """Callback to API Server"""
    get_plat_client().finish_archive(operation_id, status, error_detail)


class ArchiveResultHandler(CallbackHandler):
    """Handler for archive operation"""

    def handle(self, result: CallbackResult, poller: TaskPoller):
        if result.is_exception:
            error_detail = 'Unable to perform offline: processes were not stopped in given period'
            status = ReleaseStatus.FAILED
        else:
            error_detail = ""
            status = ReleaseStatus.SUCCESSFUL

        finish_archive(
            operation_id=poller.params["extra_params"]["operation_id"],
            status=status,
            error_detail=error_detail,
        )
