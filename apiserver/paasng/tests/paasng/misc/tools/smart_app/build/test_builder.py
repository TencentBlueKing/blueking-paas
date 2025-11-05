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
from paas_wl.infras.resources.base.exceptions import PodTimeoutError
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

    def test_start_success(self, smart_app_builder, smart_build_record):
        with (
            mock.patch.object(smart_app_builder, "launch_build_process", return_value="test-builder-pod"),
            mock.patch.object(smart_app_builder, "start_following_logs") as mock_logs,
            mock.patch.object(smart_app_builder.stream, "close") as mock_close,
            mock.patch.object(smart_app_builder.state_mgr.coordinator, "release_lock") as mock_release,
        ):
            smart_app_builder.start()

            mock_logs.assert_called_once()
            mock_close.assert_called_once()
            mock_release.assert_called_once_with(smart_build_record)

    def test_start_with_exception_in_launch(self, smart_app_builder, smart_build_record):
        """Test that resources are cleaned up when launch_build_process raises exception"""
        with (
            mock.patch.object(smart_app_builder, "launch_build_process", side_effect=Exception("Launch failed")),
            mock.patch.object(smart_app_builder.stream, "close") as mock_close,
            mock.patch.object(smart_app_builder.state_mgr.coordinator, "release_lock") as mock_release,
        ):
            with pytest.raises(Exception, match="Launch failed"):
                smart_app_builder.start()

            # Verify cleanup happens even with exception
            mock_close.assert_called_once()
            mock_release.assert_called_once_with(smart_build_record)

    def test_start_with_exception_in_following_logs(self, smart_app_builder, smart_build_record):
        """Test that resources are cleaned up when start_following_logs raises exception"""
        with (
            mock.patch.object(smart_app_builder, "launch_build_process", return_value="test-builder-pod"),
            mock.patch.object(smart_app_builder, "start_following_logs", side_effect=PodTimeoutError("Timeout")),
            mock.patch.object(smart_app_builder.stream, "close") as mock_close,
            mock.patch.object(smart_app_builder.state_mgr.coordinator, "release_lock") as mock_release,
        ):
            with pytest.raises(PodTimeoutError):
                smart_app_builder.start()

            # Verify cleanup happens
            mock_close.assert_called_once()
            mock_release.assert_called_once_with(smart_build_record)

    def test_start_following_logs(self, smart_app_builder, smart_build_record):
        """Test log following and pod completion"""
        fake_logs = [b"Building...\n", b"Build complete\n"]

        with (
            mock.patch(
                "paasng.misc.tools.smart_app.build.builder.get_default_cluster_name",
                return_value=CLUSTER_NAME_FOR_TESTING,
            ),
            mock.patch("paasng.misc.tools.smart_app.build.builder.get_client_by_cluster_name"),
            mock.patch.object(SmartBuildHandler, "wait_for_logs_readiness"),
            mock.patch.object(SmartBuildHandler, "get_build_log", return_value=iter(fake_logs)),
            mock.patch.object(SmartBuildHandler, "wait_for_succeeded"),
            mock.patch.object(smart_app_builder.stream, "write_message") as mock_write,
        ):
            smart_app_builder.start_following_logs("test-builder-pod")

            # Verify logs were written
            assert mock_write.call_count == len(fake_logs)
            mock_write.assert_any_call("Building...\n")
            mock_write.assert_any_call("Build complete\n")

            # Verify status was updated to successful
            smart_build_record.refresh_from_db()
            assert smart_build_record.status == JobStatus.SUCCESSFUL.value

    def test_launch_build_process(self, smart_app_builder):
        with (
            mock.patch(
                "paasng.misc.tools.smart_app.build.builder.get_default_cluster_name",
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
