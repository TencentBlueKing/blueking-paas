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

import types
from unittest import mock

import pytest
from django.core.cache import cache

from paas_wl.infras.cluster.shim import EnvClusterService
from paasng.platform.engine.exceptions import ServerVersionCheckFailed
from paasng.platform.engine.workflow.srv_version import ServerVersionChecker
from tests.utils.helpers import override_settings

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture()
def _clear_operator_version_cache(bk_module):
    """A fixture used to clear cache key in OperatorVersionCondition"""
    cluster_name = EnvClusterService(bk_module.get_envs("stag")).get_cluster_name()
    key = f"helm_release:{cluster_name}:operator_version"
    cache.delete(key)
    yield
    cache.delete(key)


@pytest.mark.usefixtures("_clear_operator_version_cache", "bk_cnative_app")
class TestServerVersionChecker:
    """测试校验平台服务版本一致性"""

    @pytest.mark.parametrize(
        ("apiserver_version", "operator_version", "should_raise_exception"),
        [
            # 版本一致
            ("v1.0.0", "v1.0.0", False),
            # 版本不一致
            ("v2.0.0", "v1.0.0", True),
            # operator 版本获取失败
            ("v1.0.0", "", True),
        ],
    )
    def test_validate_version(
        self,
        bk_stag_env,
        apiserver_version,
        operator_version,
        should_raise_exception,
    ):
        """触发校验, 云原生应用，开启校验，apiserver_version 非空"""
        fake_release = types.SimpleNamespace(chart=types.SimpleNamespace(app_version=operator_version))
        with (
            override_settings(
                APISERVER_OPERATOR_VERSION_CHECK=True,
                APISERVER_VERSION=apiserver_version,
            ),
            mock.patch(
                "paas_wl.infras.cluster.helm.HelmClient.get_release",
                return_value=fake_release,
            ),
        ):
            if should_raise_exception:
                with pytest.raises(ServerVersionCheckFailed):
                    ServerVersionChecker(bk_stag_env).validate_version()
            else:
                ServerVersionChecker(bk_stag_env).validate_version()
