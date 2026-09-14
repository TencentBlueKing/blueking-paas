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
    """版本为 V4 时，V4 服务地址缺失须启动即失败"""

    def test_missing_v4_url(self):
        with pytest.raises(ImproperlyConfigured, match="BK_IAM_V4_URL"):
            validate_iam_settings(IAM_VERSION_V4, {"BK_IAM_V4_URL": ""})

    def test_v3_does_not_require_v4_settings(self):
        """V3 环境无需配置 V4 相关项"""
        validate_iam_settings(IAM_VERSION_V3, {"BK_IAM_V4_URL": ""})
