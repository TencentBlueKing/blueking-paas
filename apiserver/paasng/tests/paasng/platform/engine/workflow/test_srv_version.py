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

from paas_wl.infras.cluster.shim import EnvClusterService
from paasng.platform.engine.exceptions import ServerVersionCheckFailed
from paasng.platform.engine.workflow.srv_version import ServerVersionChecker, parse_xyz_version
from tests.utils.helpers import override_settings

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

CHECKER_LOGGER = "paasng.platform.engine.workflow.srv_version"


def _patch_helm_release(operator_version: str):
    """Patch HelmClient.get_release to return the given operator version"""
    fake_release = types.SimpleNamespace(chart=types.SimpleNamespace(app_version=operator_version))
    return mock.patch("paas_wl.infras.cluster.helm.HelmClient.get_release", return_value=fake_release)


def _patch_cache(cached_operator_version: str | None = None):
    """Patch the cache used by ServerVersionChecker

    测试环境使用进程间共享的缓存(Redis), 直接读写真实缓存会与其他测试/进程相互干扰, 因此统一替换为
    Mock: 传入版本号表示缓存命中, None 表示缓存未命中.
    """
    mocked_cache = mock.MagicMock()
    mocked_cache.get.return_value = cached_operator_version
    return mock.patch("paasng.platform.engine.workflow.srv_version.cache", mocked_cache)


class TestParseXYZVersion:
    """测试从版本号中解析 X.Y.Z"""

    @pytest.mark.parametrize(
        ("version", "expected"),
        [
            ("1.8.0", (1, 8, 0)),
            ("1.7.0-beta.5", (1, 7, 0)),
            ("1.8.0-alpha.222", (1, 8, 0)),
            (" 1.8.0 ", (1, 8, 0)),
            ("v1.8.0", (1, 8, 0)),
            ("v1.7.0", (1, 7, 0)),
            ("v1.7.0-beta.1", (1, 7, 0)),
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


@pytest.mark.usefixtures("bk_cnative_app")
class TestServerVersionChecker:
    """测试校验平台服务版本兼容性"""

    @pytest.mark.parametrize(
        ("apiserver_version", "operator_version", "should_raise_exception", "expect_warning"),
        [
            # 完整版本号完全一致: 通过, 不写 WARNING
            ("1.8.0", "1.8.0", False, False),
            ("v1.8.0", "v1.8.0", False, False),
            ("v1.7.0-beta.1", "v1.7.0-beta.1", False, False),
            ("v1.8.0-beta.5", "v1.8.0-beta.5", False, False),
            # 仅一侧带 v 前缀时, 前缀不参与比较
            ("v1.8.0", "1.8.0", False, True),
            # X.Y.Z 相同, 仅预发布号不同: 放行 + WARNING
            ("1.7.0-beta.5", "1.7.0-alpha.59", False, True),
            ("v1.8.0-alpha.123", "v1.8.0-alpha.222", False, True),
            # X.Y.Z 不同: 拦截
            ("1.7.0", "1.6.0", True, False),
            ("1.8.0", "1.8.1", True, False),
            ("1.8.0-alpha.1", "1.7.0-alpha.9", True, False),
            # Helm 查询成功但 app_version 为空: 拦截
            ("1.0.0", "", True, False),
            # 版本无法解析: 拦截
            ("1.0.0", "1.7", True, False),
            ("1.7", "1.7", True, False),
            ("latest", "1.0.0", True, False),
        ],
    )
    def test_validate_version(
        self, bk_stag_env, caplog, *, apiserver_version, operator_version, should_raise_exception, expect_warning
    ):
        """触发校验, 云原生应用, 开启校验, apiserver_version 非空"""
        with (
            override_settings(APISERVER_OPERATOR_VERSION_CHECK=True, APISERVER_VERSION=apiserver_version),
            _patch_helm_release(operator_version),
            _patch_cache(),
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
            _patch_cache(),
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
            _patch_cache(),
            pytest.raises(ServerVersionCheckFailed),
        ):
            ServerVersionChecker(bk_stag_env).validate_version()

    def test_cached_version_incompatible_clears_cache(self, bk_stag_env):
        """缓存命中但 X.Y.Z 不一致: 中止部署并清理缓存, 促使下次强制刷新"""
        cluster_name = EnvClusterService(bk_stag_env).get_cluster_name()
        cache_key = f"helm_release:{cluster_name}:operator_version"

        with (
            override_settings(APISERVER_OPERATOR_VERSION_CHECK=True, APISERVER_VERSION="1.8.0"),
            mock.patch("paas_wl.infras.cluster.helm.HelmClient.get_release") as mocked_get_release,
            _patch_cache("1.7.0") as mocked_cache,
            pytest.raises(ServerVersionCheckFailed),
        ):
            ServerVersionChecker(bk_stag_env).validate_version()

        assert not mocked_get_release.called
        mocked_cache.delete.assert_called_once_with(cache_key)

    def test_cached_version_used_without_helm_query(self, bk_stag_env, caplog):
        """缓存值与 apiserver 完整一致: 不查询 Helm, 直接放行且不写 WARNING"""
        with (
            override_settings(APISERVER_OPERATOR_VERSION_CHECK=True, APISERVER_VERSION="1.8.0"),
            mock.patch("paas_wl.infras.cluster.helm.HelmClient.get_release") as mocked_get_release,
            _patch_cache("1.8.0") as mocked_cache,
            caplog.at_level(logging.WARNING, logger=CHECKER_LOGGER),
        ):
            ServerVersionChecker(bk_stag_env).validate_version()

        assert not mocked_get_release.called
        assert not mocked_cache.set.called
        assert not [r for r in caplog.records if r.levelno == logging.WARNING]

    def test_cache_written_when_full_version_matched(self, bk_stag_env):
        """查询到的 operator 版本与 apiserver 完整一致时写入缓存"""
        cluster_name = EnvClusterService(bk_stag_env).get_cluster_name()
        cache_key = f"helm_release:{cluster_name}:operator_version"

        with (
            override_settings(APISERVER_OPERATOR_VERSION_CHECK=True, APISERVER_VERSION="1.8.0"),
            _patch_helm_release("1.8.0"),
            _patch_cache() as mocked_cache,
        ):
            ServerVersionChecker(bk_stag_env).validate_version()

        mocked_cache.set.assert_called_once_with(cache_key, "1.8.0")

    def test_cache_not_written_when_only_xyz_matched(self, bk_stag_env):
        """仅 X.Y.Z 一致时放行, 但不写入缓存"""
        with (
            override_settings(APISERVER_OPERATOR_VERSION_CHECK=True, APISERVER_VERSION="1.8.0-alpha.123"),
            _patch_helm_release("1.8.0-alpha.222"),
            _patch_cache() as mocked_cache,
        ):
            ServerVersionChecker(bk_stag_env).validate_version()

        assert not mocked_cache.set.called
