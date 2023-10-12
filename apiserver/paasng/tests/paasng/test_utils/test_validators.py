# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import pytest
from django.core.exceptions import ValidationError
from django.test import TestCase

from paasng.utils.validators import DnsSafeNameValidator, ReservedWordValidator


class TestReservedWordValidator(TestCase):
    def setUp(self) -> None:
        self.validator = ReservedWordValidator("保留字测试样例")
        self.positive_sample = [
            'v20190731-001',
            'abc',
            'a-b',
            'paas-ng',
        ]
        # 保留字测试失败样本集
        self.negative_sample = ['paas-ng-dot-backend', 'v201907310us0001', 'abc--def--ghi']

    def test_positive_sample(self):
        for sample in self.positive_sample:
            assert self.validator(sample) is None

    def test_negative_sample(self):
        for sample in self.negative_sample:
            with pytest.raises(ValidationError) as exec_info:
                self.validator(sample)
            assert exec_info.value.message == self.validator.message


class TestDnsSafeNameValidator(TestCase):
    def setUp(self) -> None:
        self.validator = DnsSafeNameValidator("DNS安全名称测试样例")
        self.positive_sample = [
            'v20190731-001',
            'abc',
            'a-b',
            'paas-ng',
        ]
        # DNS安全名称测试失败样本集
        self.negative_sample = ['20190731', 'abc-', '-abc', '9bb']

    def test_positive_sample(self):
        for sample in self.positive_sample:
            assert self.validator(sample) is None

    def test_negative_sample(self):
        for sample in self.negative_sample:
            with pytest.raises(ValidationError) as exec_info:
                self.validator(sample)
            assert exec_info.value.message == self.validator.message
