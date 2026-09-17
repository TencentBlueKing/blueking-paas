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

import importlib

import pytest
from django.core.exceptions import ImproperlyConfigured

from paasng.infras.iam.base.constants import IAMVersion
from paasng.infras.iam.exceptions import BKIAMGatewayServiceError
from paasng.infras.iam.shim import (
    get_auth_backend,
    get_iam_version,
    get_management_backend,
    get_system_token,
)
from paasng.infras.iam.v3 import token as v3_token
from paasng.infras.iam.v3.auth import BKIAMV3AuthBackend
from paasng.infras.iam.v3.management import BKIAMV3ManagementBackend
from paasng.infras.iam.v4.management import BKIAMV4ManagementBackend


class TestGetIAMVersion:
    def test_v3(self, settings):
        settings.BK_IAM_VERSION = "v3"
        assert get_iam_version() == IAMVersion.V3

    def test_unsupported_version_raises(self, settings):
        settings.BK_IAM_VERSION = "v5"
        with pytest.raises(ImproperlyConfigured, match="不支持的 IAM 版本: v5"):
            get_iam_version()


class TestBackendDispatch:
    def test_dispatch_auth_backend_to_v3(self, settings):
        settings.BK_IAM_VERSION = "v3"
        assert isinstance(get_auth_backend(), BKIAMV3AuthBackend)

    def test_dispatch_management_backend_to_v3(self, settings):
        settings.BK_IAM_VERSION = "v3"
        backend = get_management_backend("tenant-foo")
        assert isinstance(backend, BKIAMV3ManagementBackend)
        assert backend.tenant_id == "tenant-foo"

    def test_dispatch_management_backend_to_v4(self, settings):
        settings.BK_IAM_VERSION = "v4"
        backend = get_management_backend("tenant-foo", operator="someone")
        assert isinstance(backend, BKIAMV4ManagementBackend)
        assert backend.tenant_id == "tenant-foo"
        assert backend.operator == "someone"


class TestSystemTokenDispatch:
    """取系统令牌同样按版本分发，两侧的失败形态须收敛成同一种异常"""

    @pytest.mark.parametrize(
        ("version", "module_path"),
        [
            pytest.param("v3", "paasng.infras.iam.v3.token", id="v3"),
            pytest.param("v4", "paasng.infras.iam.v4.token", id="v4"),
        ],
    )
    def test_dispatch_by_version(self, settings, monkeypatch, version, module_path):
        settings.BK_IAM_VERSION = version
        module = importlib.import_module(module_path)
        monkeypatch.setattr(module, "fetch_system_token", lambda tenant_id: f"token-from-{version}")

        assert get_system_token("tenant-foo") == f"token-from-{version}"

    def test_unexpected_error_is_converted(self, settings, monkeypatch):
        """SDK 自身的异常也要收敛，否则会越过调用方的 except 变成 500"""
        settings.BK_IAM_VERSION = "v3"

        def _raise(tenant_id: str) -> str:
            raise ValueError("Expecting value: line 1 column 1")

        monkeypatch.setattr(v3_token, "fetch_system_token", _raise)

        with pytest.raises(BKIAMGatewayServiceError):
            get_system_token("tenant-foo")
