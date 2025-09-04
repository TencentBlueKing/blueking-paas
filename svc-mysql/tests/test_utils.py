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

import string

import pytest
from svc_mysql.vendor.utils import generate_mysql_password


@pytest.mark.django_db
class TestGenerateStrongPassword:
    def test_length_validation(self):
        """测试密码长度校验"""
        with pytest.raises(ValueError, match="Password length must be 8 characters or more"):
            generate_mysql_password(7, [])

    def test_dictionary_word_validation(self):
        """测试字典词长度校验"""
        with pytest.raises(
            ValueError, match="Dictionary word 'abc' is shorter than 4 characters and does not meet the requirement"
        ):
            generate_mysql_password(8, ["abc"])

    @pytest.mark.parametrize("length", [8, 10, 16, 32])
    def test_basic_password_structure(self, length):
        """测试密码基本结构是否符合要求"""
        password = generate_mysql_password(length, [])
        assert len(password) == length

        # 检查是否包含四种字符类型
        has_lower = any(c in string.ascii_lowercase for c in password)
        has_upper = any(c in string.ascii_uppercase for c in password)
        has_digit = any(c in string.digits for c in password)
        has_special = any(c in r"""_+-,&=!@#$%^*().|""" for c in password)

        assert has_lower
        assert has_upper
        assert has_digit
        assert has_special

    def test_forbidden_words(self):
        """测试密码不包含禁用字典词"""
        forbidden_words = ["password", "admin123", "testuser"]
        password = generate_mysql_password(12, forbidden_words)

        for word in forbidden_words:
            assert word not in password
