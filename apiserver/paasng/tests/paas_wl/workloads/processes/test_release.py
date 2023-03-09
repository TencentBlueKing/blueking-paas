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
import uuid
from unittest import mock

import pytest
from blue_krill.async_utils.poll_task import CallbackResult, CallbackStatus

from paas_wl.release_controller.process.callbacks import ReleaseResultHandler
from paas_wl.utils.constants import CommandStatus as JobStatus
from tests.utils.mocks.poll_task import FakeTaskPoller


class TestReleaseResultHandler:
    """Tests for ReleaseResultHandler"""

    @pytest.fixture
    def deployment_id(self):
        return uuid.uuid4()

    @pytest.mark.parametrize(
        'result,status,error_detail',
        [
            (
                CallbackResult(status=CallbackStatus.EXCEPTION),
                JobStatus.FAILED,
                'Release failed, internal error',
            ),
            (CallbackResult(status=CallbackStatus.NORMAL), JobStatus.SUCCESSFUL, ''),
            (CallbackResult(status=CallbackStatus.NORMAL, data={'aborted': False}), JobStatus.SUCCESSFUL.value, ''),
            (
                # `data` is not a valid AbortedDetails object
                CallbackResult(status=CallbackStatus.NORMAL, data={'aborted': True}),
                JobStatus.SUCCESSFUL,
                '',
            ),
            (
                CallbackResult(
                    status=CallbackStatus.NORMAL,
                    data={'aborted': True, 'policy': {'reason': 'foo', 'name': 'foo_policy'}},
                ),
                JobStatus.FAILED,
                'Release aborted, reason: foo',
            ),
            (
                CallbackResult(
                    status=CallbackStatus.NORMAL,
                    data={'aborted': True, 'policy': {'reason': 'foo', 'name': 'foo_policy', 'is_interrupted': True}},
                ),
                JobStatus.INTERRUPTED,
                'Release aborted, reason: foo',
            ),
        ],
    )
    def test_failed(self, result, status, error_detail, deployment_id):
        with mock.patch("paas_wl.release_controller.process.callbacks.finish_release") as mocked:
            ReleaseResultHandler().handle(
                result, FakeTaskPoller.create({'extra_params': {'deployment_id': deployment_id}})
            )

        assert mocked.call_count == 1
        assert mocked.call_args[1]["deployment_id"] == deployment_id
        assert mocked.call_args[1]["status"] == status
        assert mocked.call_args[1]["error_detail"] == error_detail
