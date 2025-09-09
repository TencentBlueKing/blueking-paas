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
from paasng.misc.tools.smart_app.constants import SmartBuildPhaseType
from paasng.misc.tools.smart_app.models import SmartBuildRecord
from paasng.platform.engine.constants import JobStatus
from tests.paasng.misc.tools.smart_app.setup_utils import create_fake_smart_build

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


source_package_url = "https://example.com/source.tar.gz"


@pytest.fixture()
def smart_build_record() -> SmartBuildRecord:
    """创建一个 SmartBuildRecord 实例用于测试"""
    return create_fake_smart_build()


@pytest.fixture()
def smart_app_builder(smart_build_record, tmp_path) -> SmartAppBuilder:
    """创建 SmartAppBuilder 实例用于测试"""
    package_path = tmp_path / "test_package.tar.gz"
    package_path.touch()  # 创建一个空文件

    with (
        patch("paasng.misc.tools.smart_app.build.builder.SmartBuildStateMgr"),
        patch("paasng.misc.tools.smart_app.build.builder.make_channel_stream"),
        patch("paasng.misc.tools.smart_app.build.builder.SmartBuildCoordinator"),
    ):
        builder = SmartAppBuilder(smart_build_record, source_package_url, package_path)
        return builder


class TestSmartAppBuilder:
    """测试 SmartAppBuilder 类的核心功能"""

    def test_start_success(self, smart_app_builder):
        """测试成功启动构建流程"""
        with (
            patch("paasng.misc.tools.smart_app.build.builder.start_phase") as mock_start_phase,
            patch("paasng.misc.tools.smart_app.build.builder.end_phase") as mock_end_phase,
        ):
            # 模拟验证应用描述文件成功
            smart_app_builder.validate_app_description = Mock()
            smart_app_builder.async_start_build_process = Mock()

            smart_app_builder.start()

            # 验证阶段开始和结束
            mock_start_phase.assert_called_once_with(
                smart_app_builder.smart_build, smart_app_builder.stream, SmartBuildPhaseType.PREPARATION
            )
            mock_end_phase.assert_called_once_with(
                smart_app_builder.smart_build,
                smart_app_builder.stream,
                JobStatus.SUCCESSFUL,
                SmartBuildPhaseType.PREPARATION,
            )

            # 验证方法调用
            smart_app_builder.validate_app_description.assert_called_once()
            smart_app_builder.async_start_build_process.assert_called_once()

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
    with patch("paasng.misc.tools.smart_app.build.builder.ClusterAllocator") as mock_allocator_class:
        mock_allocator_class.return_value.get_default.return_value = "test-cluster"

        result = get_default_cluster_name()
        assert result == "test-cluster"

        mock_allocator_class.assert_called_once()
        mock_allocator_class.return_value.get_default.assert_called_once()
