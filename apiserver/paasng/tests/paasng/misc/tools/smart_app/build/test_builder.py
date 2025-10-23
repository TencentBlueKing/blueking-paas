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
from paasng.misc.tools.smart_app.build.poller import SmartBuildProcessPoller
from paasng.misc.tools.smart_app.models import SmartBuildRecord
from tests.paasng.misc.tools.smart_app.setup_utils import create_fake_smart_build
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

SOURCE_GET_URL = "https://example.com/source.tar.gz"
DEST_PUT_URL = "https://example.com/dest.tar.gz"
ARTIFACT_DOWNLOAD_URL = "https://example.com/artifact.tar.gz"


@pytest.fixture()
def smart_build_record() -> SmartBuildRecord:
    return create_fake_smart_build()


@pytest.fixture()
def smart_app_builder(smart_build_record) -> SmartAppBuilder:
    with (
        mock.patch("paasng.misc.tools.smart_app.build.flow.SmartBuildStateMgr"),
        mock.patch("paasng.misc.tools.smart_app.output.make_channel_stream"),
    ):
        return SmartAppBuilder(smart_build_record, SOURCE_GET_URL, DEST_PUT_URL, ARTIFACT_DOWNLOAD_URL)


class TestSmartAppBuilder:
    """Tests for SmartAppBuilder"""

    @mock.patch("paasng.misc.tools.smart_app.build.builder.start_phase")
    @mock.patch("paasng.misc.tools.smart_app.build.builder.end_phase")
    def test_start_success(self, mock_start, mock_end, smart_app_builder):
        with (
            mock.patch.object(smart_app_builder, "validate_app_description") as mock_validate,
            mock.patch.object(smart_app_builder, "_start_build_process") as mock_start_build,
            mock.patch.object(smart_app_builder, "_final_builder") as mock_final_builder,
            mock.patch("paasng.misc.tools.smart_app.build.builder.SmartBuildProcessPoller"),
        ):
            smart_app_builder.start()

            mock_validate.assert_called_once()
            mock_start_build.assert_called_once()
            mock_final_builder.assert_called_once()
            assert mock_start.call_count == 2
            assert mock_end.call_count == 2

    @mock.patch.object(SmartBuildProcessPoller, "start")
    def test_start_build_process(self, mock_start, smart_app_builder):
        with (
            mock.patch.object(smart_app_builder, "launch_build_process") as mock_launch,
            mock.patch.object(smart_app_builder, "start_following_logs") as mock_logs,
        ):
            smart_app_builder._start_build_process(mock.Mock())

            mock_launch.assert_called_once()
            mock_logs.assert_called_once()
            mock_start.assert_called_once()

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
