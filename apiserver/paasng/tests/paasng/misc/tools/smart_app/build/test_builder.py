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

from unittest import mock

import pytest

from paas_wl.bk_app.deploy.app_res.controllers import NamespacesHandler
from paasng.misc.tools.smart_app.build.builder import SmartAppBuilder
from paasng.misc.tools.smart_app.build.handler import SmartBuildHandler
from paasng.misc.tools.smart_app.models import SmartBuildRecord
from paasng.platform.engine.constants import JobStatus
from tests.paasng.misc.tools.smart_app.setup_utils import create_fake_smart_build
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

SOURCE_GET_URL = "https://example.com/source.tar.gz"
DEST_PUT_URL = "https://example.com/dest.tar.gz"


@pytest.fixture()
def smart_build_record() -> SmartBuildRecord:
    return create_fake_smart_build()


@pytest.fixture()
def smart_app_builder(smart_build_record) -> SmartAppBuilder:
    """Create a SmartAppBuilder instance for testing"""
    return SmartAppBuilder(smart_build_record, SOURCE_GET_URL, DEST_PUT_URL)


class TestSmartAppBuilder:
    """Tests for SmartAppBuilder"""

    def test_start_success(self, smart_app_builder):
        with (
            mock.patch.object(smart_app_builder.state_mgr, "start") as mock_start,
            mock.patch.object(smart_app_builder, "launch_build_process", return_value="test-builder-pod"),
            mock.patch.object(smart_app_builder, "start_following_logs") as mock_logs,
            mock.patch.object(smart_app_builder.state_mgr, "finish") as mock_finish,
        ):
            smart_app_builder.start()

            mock_start.assert_called_once()
            mock_logs.assert_called_once_with("test-builder-pod")
            mock_finish.assert_called_once_with(JobStatus.SUCCESSFUL)

    def test_launch_build_process(self, smart_app_builder):
        with (
            mock.patch.object(
                SmartAppBuilder,
                "_get_default_cluster_name",
                return_value=CLUSTER_NAME_FOR_TESTING,
            ),
            mock.patch(
                "paasng.misc.tools.smart_app.build.builder.get_client_by_cluster_name",
            ) as mock_get_client,
            mock.patch.object(NamespacesHandler, "ensure_namespace") as mock_ensure,
            mock.patch.object(SmartBuildHandler, "build_pod") as mock_build_pod,
        ):
            smart_app_builder.launch_build_process()

            mock_get_client.assert_called_once_with(CLUSTER_NAME_FOR_TESTING)
            mock_ensure.assert_called_once()
            mock_build_pod.assert_called_once()
