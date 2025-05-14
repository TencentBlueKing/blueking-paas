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

import pytest
from django.core.exceptions import ValidationError

from paasng.utils.validators import DnsSafeNameValidator, ReservedWordValidator


class TestReservedWordValidator:
    @pytest.mark.parametrize("input_str", ["v20190731-001", "abc", "a-b", "paas-ng"])
    def test_valid_input(self, input_str):
        validator = ReservedWordValidator("保留字测试样例")
        assert validator(input_str) is None

    @pytest.mark.parametrize("input_str", ["paas-ng-dot-backend", "v201907310us0001", "abc--def--ghi"])
    def test_invalid_input(self, input_str):
        validator = ReservedWordValidator("保留字测试样例")
        with pytest.raises(ValidationError) as exec_info:
            validator(input_str)
        assert exec_info.value.message == validator.message


class TestDnsSafeNameValidator:
    @pytest.mark.parametrize("input_str", ["v20190731-001", "abc", "a-b", "paas-ng"])
    def test_valid_input(self, input_str):
        validator = DnsSafeNameValidator("DNS安全名称测试样例")
        assert validator(input_str) is None

    @pytest.mark.parametrize("input_str", ["20190731", "abc-", "-abc", "9bb"])
    def test_negative_sample(self, input_str):
        validator = DnsSafeNameValidator("DNS安全名称测试样例")
        with pytest.raises(ValidationError) as exec_info:
            validator(input_str)
        assert exec_info.value.message == validator.message
