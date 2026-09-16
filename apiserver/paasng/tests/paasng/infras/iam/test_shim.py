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

import pytest
from django.core.exceptions import ImproperlyConfigured

from paasng.infras.iam.base.constants import IAMVersion
from paasng.infras.iam.shim import (
    get_auth_backend,
    get_iam_version,
    get_management_backend,
)
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

    def test_system_operator_uses_app_code(self, settings):
        settings.BK_APP_CODE = "bk_paas"
        from paasng.infras.iam.shim import get_system_operator

        assert get_system_operator() == "bk_paas"
