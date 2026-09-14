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

from paasng.infras.iam.exceptions import BKIAMCapabilityNotSupportedError
from paasng.infras.iam.v4.management import BKIAMV4ManagementBackend


@pytest.fixture()
def backend() -> BKIAMV4ManagementBackend:
    return BKIAMV4ManagementBackend("tenant-foo")


class TestCapabilityNotSupported:
    def test_update_management_space_scopes(self, backend):
        """V4 暂缺的管理接口必须明确抛异常，不能静默返回成功"""
        with pytest.raises(BKIAMCapabilityNotSupportedError) as exc_info:
            backend.update_management_space_scopes(1, "app-code", "App", "-1")

        assert exc_info.value.capability == "更新管理空间的授权范围"
        assert "V4 暂未提供该能力" in str(exc_info.value)
