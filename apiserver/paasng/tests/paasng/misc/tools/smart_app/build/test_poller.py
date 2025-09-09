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

import pytest
from blue_krill.async_utils.poll_task import CallbackResult, CallbackStatus

from paasng.misc.tools.smart_app.build.poller import BuildProcessResultHandler
from paasng.platform.engine.constants import JobStatus
from tests.utils.mocks.poll_task import FakeTaskPoller

pytestmark = pytest.mark.django_db


class TestBuildProcessResultHandler:
    """Tests for BuildProcessResultHandler"""

    def test_succeeded(self, smart_build):
        params = {"smart_build_id": smart_build.uuid}
        result = CallbackResult(
            status=CallbackStatus.NORMAL,
            data={"smart_build_id": smart_build.uuid, "build_status": JobStatus.SUCCESSFUL.value},
        )

        BuildProcessResultHandler().handle(result, FakeTaskPoller.create(params))
        smart_build.refresh_from_db()
        assert smart_build.status == JobStatus.SUCCESSFUL.value

    @pytest.mark.parametrize(
        ("callback_status", "status"),
        [
            (CallbackStatus.EXCEPTION, JobStatus.FAILED.value),
            (CallbackStatus.NORMAL, JobStatus.FAILED.value),
        ],
    )
    def test_failed(self, callback_status, status, smart_build):
        params = {"smart_build_id": smart_build.uuid}
        result = CallbackResult(
            status=callback_status, data={"smart_build_id": smart_build.uuid, "build_status": status}
        )

        BuildProcessResultHandler().handle(result, FakeTaskPoller.create(params))
        smart_build.refresh_from_db()
        assert smart_build.status == status
