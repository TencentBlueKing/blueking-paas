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

from paasng.settings.utils import IAM_VERSION_V3, IAM_VERSION_V4, validate_iam_settings

COMPLETE_V4_SETTINGS = {
    "BK_IAM_V4_URL": "http://bkiam.example.com",
    "BK_IAM_V4_APP_CODE": "bk_paas3",
    "BK_IAM_V4_APP_SECRET": "secret",
    "IAM_PAAS_V4_SYSTEM_ID": "bk_paas3",
}


class TestVersionValidation:
    """版本开关取值非法时须启动即失败，不静默降级"""

    @pytest.mark.parametrize("version", [IAM_VERSION_V3, IAM_VERSION_V4])
    def test_supported_versions(self, version):
        validate_iam_settings(version, COMPLETE_V4_SETTINGS)

    @pytest.mark.parametrize("version", ["v5", "V3", "", "3"])
    def test_unsupported_version(self, version):
        with pytest.raises(ImproperlyConfigured, match=f"不支持的 IAM 版本: {version}"):
            validate_iam_settings(version, COMPLETE_V4_SETTINGS)


class TestV4RequiredSettings:
    """版本为 V4 时，必填配置缺失须启动即失败并指明缺失项"""

    @pytest.mark.parametrize(
        "missing_name",
        ["BK_IAM_V4_URL", "BK_IAM_V4_APP_CODE", "BK_IAM_V4_APP_SECRET", "IAM_PAAS_V4_SYSTEM_ID"],
    )
    def test_single_missing_setting(self, missing_name):
        v4_settings = {**COMPLETE_V4_SETTINGS, missing_name: ""}

        with pytest.raises(ImproperlyConfigured, match=missing_name):
            validate_iam_settings(IAM_VERSION_V4, v4_settings)

    def test_reports_all_missing_settings(self):
        v4_settings = {**COMPLETE_V4_SETTINGS, "BK_IAM_V4_URL": "", "BK_IAM_V4_APP_SECRET": None}

        with pytest.raises(ImproperlyConfigured) as exc_info:
            validate_iam_settings(IAM_VERSION_V4, v4_settings)

        assert "BK_IAM_V4_URL" in str(exc_info.value)
        assert "BK_IAM_V4_APP_SECRET" in str(exc_info.value)

    def test_v3_does_not_require_v4_settings(self):
        """V3 环境无需配置 V4 相关项"""
        validate_iam_settings(IAM_VERSION_V3, dict.fromkeys(COMPLETE_V4_SETTINGS, ""))
