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

from unittest.mock import Mock, patch

import pytest
from django.conf import settings

from paasng.misc.tools.smart_app.build.builder import (
    SmartAppBuilder,
    get_default_cluster_name,
)
from paasng.misc.tools.smart_app.models import SmartBuildRecord
from tests.paasng.misc.tools.smart_app.setup_utils import create_fake_smart_build

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

SOURCE_GET_URL = "https://example.com/source.tar.gz"
DEST_PUT_URL = "https://example.com/dest.tar.gz"


@pytest.fixture()
def smart_build_record() -> SmartBuildRecord:
    return create_fake_smart_build()


@pytest.fixture()
def smart_app_builder(smart_build_record, tmp_path) -> SmartAppBuilder:
    package_path = tmp_path / "test_package.tar.gz"
    package_path.touch()

    with (
        patch("paasng.misc.tools.smart_app.build.builder.SmartBuildStateMgr"),
        patch("paasng.misc.tools.smart_app.build.builder.make_channel_stream"),
    ):
        return SmartAppBuilder(smart_build_record, SOURCE_GET_URL, DEST_PUT_URL)


class TestSmartAppBuilder:
    """测试 SmartAppBuilder 类的核心功能"""

    def test_start_success(self, smart_app_builder):
        smart_app_builder.validate_app_description = Mock()

        with (
            patch("paasng.misc.tools.smart_app.build.builder.start_phase") as mock_start,
            patch("paasng.misc.tools.smart_app.build.builder.end_phase") as mock_end,
            patch.object(smart_app_builder, "launch_build_process", return_value="test-builder"),
            patch.object(smart_app_builder, "start_following_logs"),
            patch("paasng.misc.tools.smart_app.build.builder.SmartBuildProcessPoller"),
        ):
            smart_app_builder.start()

            assert mock_start.call_count == 2
            assert mock_end.call_count == 2
            smart_app_builder.validate_app_description.assert_called_once()

    def test_launch_build_process(self, smart_app_builder):
        """测试启动构建进程"""
        mock_client = Mock()
        mock_handler = Mock()
        with (
            patch("paasng.misc.tools.smart_app.build.builder.get_default_cluster_name", return_value="test-cluster"),
            patch(
                "paasng.misc.tools.smart_app.build.builder.get_default_builder_namespace",
                return_value="smart-app-builder",
            ),
            patch("paasng.misc.tools.smart_app.build.builder.generate_builder_name", return_value="test-builder-name"),
            patch("paasng.misc.tools.smart_app.build.builder.get_client_by_cluster_name", return_value=mock_client),
            patch(
                "paasng.misc.tools.smart_app.build.builder.SmartBuildHandler", return_value=mock_handler
            ) as mock_handler_class,
            patch("paasng.misc.tools.smart_app.build.builder.ensure_namespace", return_value=True),
        ):
            smart_app_builder.launch_build_process()

            # 验证构建处理器被调用
            mock_handler_class.assert_called_once_with(mock_client)
            mock_handler.build_pod.assert_called_once()

            # 验证模板参数
            call_args = mock_handler.build_pod.call_args[1]
            template = call_args["template"]
            assert template.name == "test-builder-name"
            assert template.namespace == "smart-app-builder"
            assert template.runtime.image == settings.SMART_BUILDER_IMAGE
            assert "SOURCE_GET_URL" in template.runtime.envs
            assert "DEST_PUT_URL" in template.runtime.envs
            assert "BUILDER_SHIM_IMAGE" in template.runtime.envs


def test_get_default_cluster_name():
    """测试获取默认集群名称"""
    with patch("paasng.misc.tools.smart_app.build.builder.ClusterAllocator") as mock_allocator:
        mock_cluster = Mock()
        mock_cluster.name = "test-cluster"
        mock_allocator.return_value.get_default.return_value = mock_cluster

        assert get_default_cluster_name() == "test-cluster"
