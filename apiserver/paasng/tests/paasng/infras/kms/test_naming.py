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

from paasng.infras.kms import naming
from paasng.infras.kms.exceptions import KMSValidationError

VERSION_ID = "0b1f4c2e-8d3a-4f6b-9c1d-2e3f4a5b6c7d"
VERSION_HEX = "0b1f4c2e8d3a4f6b9c1d2e3f4a5b6c7d"


class TestBuildCredentialName:
    def test_format(self):
        name = naming.build_credential_name(app_code="demo", module_name="web", env_name="prod", version_id=VERSION_ID)
        assert name == f"demo-web-prod-{VERSION_HEX}"

    def test_long_prefix_is_truncated_and_version_suffix_kept(self):
        name = naming.build_credential_name(
            app_code="a" * 200, module_name="web", env_name="prod", version_id=VERSION_ID
        )
        assert len(name) <= 128
        assert name.endswith(f"-{VERSION_HEX}")

    def test_invalid_characters_are_sanitized(self):
        name = naming.build_credential_name(
            app_code="My_App", module_name="web.v2", env_name="prod", version_id=VERSION_ID
        )
        assert name == f"my-app-web-v2-prod-{VERSION_HEX}"

    def test_rejects_version_id_that_is_not_uuid(self):
        with pytest.raises(KMSValidationError):
            naming.build_credential_name(app_code="demo", module_name="web", env_name="prod", version_id="v1")


class TestValidateCredentialName:
    @pytest.mark.parametrize("name", ["a", "demo-web-prod-0b1f", "a1-b2"])
    def test_accepts_valid_names(self, name):
        naming.validate_credential_name(name)

    @pytest.mark.parametrize("name", ["", "Upper", "a.b", "a_b", "-lead", "trail-", "x" * 129])
    def test_rejects_invalid_names(self, name):
        with pytest.raises(KMSValidationError):
            naming.validate_credential_name(name)


class TestOpenBaoKeyAndRole:
    def test_key_and_role_format(self):
        kwargs = {"tenant_id": "default", "scope_type": "scope", "scope_name": "blueking", "credential_name": "mysql"}
        assert naming.build_openbao_key(**kwargs) == "default/scope/blueking/secret/mysql"
        assert naming.build_kms_role(**kwargs) == "default.scope.blueking.secret.mysql"

    @pytest.mark.parametrize("field", ["tenant_id", "scope_type", "scope_name"])
    @pytest.mark.parametrize("value", ["a/b", "a.b", "", None])
    def test_rejects_unsafe_path_segments(self, field, value):
        kwargs = {"tenant_id": "default", "scope_type": "scope", "scope_name": "blueking"}
        kwargs[field] = value
        with pytest.raises(KMSValidationError):
            naming.build_openbao_key(credential_name="mysql", **kwargs)
        with pytest.raises(KMSValidationError):
            naming.build_kms_role(credential_name="mysql", **kwargs)


class TestResourceNames:
    def test_resource_name_includes_tenant(self):
        name = naming.build_resource_name(tenant_id="default", credential_name=f"demo-web-prod-{VERSION_HEX}")
        assert name == f"kms-default-demo-web-prod-{VERSION_HEX}"

    def test_resource_name_sanitizes_tenant(self):
        name = naming.build_resource_name(tenant_id="Tenant_1", credential_name="demo")
        assert name == "kms-tenant-1-demo"

    def test_service_account_name_has_no_version(self):
        name = naming.build_service_account_name(app_code="demo", module_name="web", env_name="prod")
        assert name == "demo-web-prod-kms"
