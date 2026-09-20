# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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
import types
from unittest import mock

import pytest
from django.core.cache import cache

from paas_wl.infras.cluster.shim import EnvClusterService
from paasng.platform.engine.exceptions import ServerVersionCheckFailed
from paasng.platform.engine.workflow.srv_version import ServerVersionChecker, parse_xyz_version
from tests.utils.helpers import override_settings

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

CHECKER_LOGGER = "paasng.platform.engine.workflow.srv_version"


@pytest.fixture()
def _clear_operator_version_cache(bk_module):
    """A fixture used to clear cache key in OperatorVersionCondition"""
    cluster_name = EnvClusterService(bk_module.get_envs("stag")).get_cluster_name()
    key = f"helm_release:{cluster_name}:operator_version"
    cache.delete(key)
    yield
    cache.delete(key)


def _patch_helm_release(operator_version: str):
    """Patch HelmClient.get_release to return the given operator version"""
    fake_release = types.SimpleNamespace(chart=types.SimpleNamespace(app_version=operator_version))
    return mock.patch("paas_wl.infras.cluster.helm.HelmClient.get_release", return_value=fake_release)


class TestParseXYZVersion:
    """测试从版本号中解析 X.Y.Z"""

    @pytest.mark.parametrize(
        ("version", "expected"),
        [
            ("1.8.0", (1, 8, 0)),
            ("1.7.0-beta.5", (1, 7, 0)),
            ("1.8.0-alpha.222", (1, 8, 0)),
            (" 1.8.0 ", (1, 8, 0)),
            # 解析不出三段数字的版本号
            ("1.7", None),
            ("1", None),
            ("v1.8", None),
            ("1.8.0.1", None),
            ("1.8.x", None),
            # 预发布号/构建信息不能为空
            ("1.8.0-", None),
            ("1.8.0+", None),
            ("latest", None),
            ("", None),
            (None, None),
        ],
    )
    def test_parse_xyz_version(self, version, expected):
        assert parse_xyz_version(version) == expected


@pytest.mark.usefixtures("_clear_operator_version_cache", "bk_cnative_app")
class TestServerVersionChecker:
    """测试校验平台服务版本兼容性"""

    @pytest.mark.parametrize(
        ("apiserver_version", "operator_version", "should_raise_exception", "expect_warning"),
        [
            # 完整版本号完全一致: 通过, 不写 WARNING
            ("1.8.0", "1.8.0", False, False),
            ("1.8.0-beta.5", "1.8.0-beta.5", False, False),
            # X.Y.Z 相同, 仅预发布号不同: 放行 + WARNING
            ("1.7.0-beta.5", "1.7.0-alpha.59", False, True),
            ("1.8.0-alpha.123", "1.8.0-alpha.222", False, True),
            # X.Y.Z 不同: 拦截
            ("1.7.0", "1.6.0", True, False),
            ("1.8.0", "1.8.1", True, False),
            ("1.8.0-alpha.1", "1.7.0-alpha.9", True, False),
            # Helm 查询成功但 app_version 为空: 拦截
            ("v1.0.0", "", True, False),
            # 版本无法解析: 拦截
            ("v1.0.0", "1.7", True, False),
            ("1.7", "1.7", True, False),
            ("latest", "v1.0.0", True, False),
        ],
    )
    def test_validate_version(
        self, bk_stag_env, caplog, *, apiserver_version, operator_version, should_raise_exception, expect_warning
    ):
        """触发校验, 云原生应用, 开启校验, apiserver_version 非空"""
        with (
            override_settings(APISERVER_OPERATOR_VERSION_CHECK=True, APISERVER_VERSION=apiserver_version),
            _patch_helm_release(operator_version),
            caplog.at_level(logging.WARNING, logger=CHECKER_LOGGER),
        ):
            if should_raise_exception:
                with pytest.raises(ServerVersionCheckFailed):
                    ServerVersionChecker(bk_stag_env).validate_version()
            else:
                ServerVersionChecker(bk_stag_env).validate_version()

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == (1 if expect_warning else 0)
        if expect_warning:
            assert apiserver_version in warnings[0].getMessage()
            assert operator_version in warnings[0].getMessage()

    def test_error_message_contains_both_full_versions(self, bk_stag_env):
        """X.Y.Z 不同时, 报错信息中需要带上两边的完整版本号"""
        with (
            override_settings(APISERVER_OPERATOR_VERSION_CHECK=True, APISERVER_VERSION="1.8.0-alpha.222"),
            _patch_helm_release("1.8.1-alpha.1"),
            pytest.raises(ServerVersionCheckFailed) as exc_info,
        ):
            ServerVersionChecker(bk_stag_env).validate_version()

        assert "1.8.0-alpha.222" in str(exc_info.value)
        assert "1.8.1-alpha.1" in str(exc_info.value)

    def test_operator_version_query_failed(self, bk_stag_env):
        """Helm 查询 operator 版本失败时, 中止部署"""
        with (
            override_settings(APISERVER_OPERATOR_VERSION_CHECK=True, APISERVER_VERSION="1.8.0"),
            mock.patch("paas_wl.infras.cluster.helm.HelmClient.get_release", side_effect=RuntimeError("helm error")),
            pytest.raises(ServerVersionCheckFailed),
        ):
            ServerVersionChecker(bk_stag_env).validate_version()

    def test_cache_written_when_full_version_matched(self, bk_stag_env):
        """完整版本号一致时写入缓存"""
        cluster_name = EnvClusterService(bk_stag_env).get_cluster_name()
        cache_key = f"helm_release:{cluster_name}:operator_version"

        with (
            override_settings(APISERVER_OPERATOR_VERSION_CHECK=True, APISERVER_VERSION="1.8.0"),
            _patch_helm_release("1.8.0"),
        ):
            ServerVersionChecker(bk_stag_env).validate_version()

        assert cache.get(cache_key) == "1.8.0"

    def test_cached_operator_version_is_used(self, bk_stag_env):
        """缓存命中时不需要查询 Helm"""
        cluster_name = EnvClusterService(bk_stag_env).get_cluster_name()
        cache_key = f"helm_release:{cluster_name}:operator_version"
        cache.set(cache_key, "1.8.0")

        with (
            override_settings(APISERVER_OPERATOR_VERSION_CHECK=True, APISERVER_VERSION="1.8.0"),
            mock.patch("paas_wl.infras.cluster.helm.HelmClient.get_release") as mocked_get_release,
        ):
            ServerVersionChecker(bk_stag_env).validate_version()

        assert not mocked_get_release.called

    def test_cache_not_written_when_only_xyz_matched(self, bk_stag_env):
        """仅 X.Y.Z 一致时, 放行但不写入缓存"""
        cluster_name = EnvClusterService(bk_stag_env).get_cluster_name()
        cache_key = f"helm_release:{cluster_name}:operator_version"

        with (
            override_settings(APISERVER_OPERATOR_VERSION_CHECK=True, APISERVER_VERSION="1.8.0-alpha.123"),
            _patch_helm_release("1.8.0-alpha.222"),
        ):
            ServerVersionChecker(bk_stag_env).validate_version()

        assert cache.get(cache_key) is None

    def test_cache_cleared_when_versions_incompatible(self, bk_stag_env):
        """缓存中的 operator 版本与 apiserver 不兼容时, 清理缓存促使下次强制刷新"""
        cluster_name = EnvClusterService(bk_stag_env).get_cluster_name()
        cache_key = f"helm_release:{cluster_name}:operator_version"
        cache.set(cache_key, "1.7.0")

        with (
            override_settings(APISERVER_OPERATOR_VERSION_CHECK=True, APISERVER_VERSION="1.8.0"),
            pytest.raises(ServerVersionCheckFailed),
        ):
            ServerVersionChecker(bk_stag_env).validate_version()

        assert cache.get(cache_key) is None
