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

import re

from django.test import TestCase


class TestAnsiEscapeFilter(TestCase):
    """测试ANSI转义序列过滤功能"""

    def setUp(self):
        """准备测试所需的正则表达式对象"""
        self.ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    def test_ansi_escape_filtering(self):
        """测试过滤各种类型的 ANSI 转义序列"""
        # 测试用例：包含各种ANSI转义序列的文本
        test_cases = [
            # 简单的颜色代码
            ("\033[31mError message\033[0m", "Error message"),
            # 粗体文本
            ("\033[1mBold text\033[0m", "Bold text"),
            # 背景色
            ("\033[41mRed background\033[0m", "Red background"),
            # 复杂组合
            ("\033[1;32;40mComplex formatting\033[0m", "Complex formatting"),
            # 光标移动
            ("Start\033[5DBack", "StartBack"),
            # 清除行
            ("Line content\033[2K", "Line content"),
            # 多种转义序列混合
            ("\033[32mGreen\033[0m \033[1mBold\033[0m \033[4mUnderline\033[0m", "Green Bold Underline"),
            # 不含转义序列的普通文本
            ("Normal text without escape sequences", "Normal text without escape sequences"),
        ]

        # 验证每个测试用例
        for input_text, expected_output in test_cases:
            filtered_text = self.ansi_escape.sub("", input_text)
            assert filtered_text == expected_output, f"Failed to filter ANSI escape sequences from: {repr(input_text)}"

    def test_deployment_log_filtering(self):
        """测试实际部署日志的 ANSI 转义序列过滤"""
        # 模拟部署日志
        sample_log = (
            "\033[34m[2025-03-27 20:01:14]\033[0m \033[32mINFO\033[0m: Starting build process...\n"
            "\033[31mERROR\033[0m: Build failed with code 1\n"
            "\033[33mWARNING\033[0m: Deployment interrupted by user"
        )

        expected_clean_log = (
            "[2025-03-27 20:01:14] INFO: Starting build process...\n"
            "ERROR: Build failed with code 1\n"
            "WARNING: Deployment interrupted by user"
        )

        filtered_log = self.ansi_escape.sub("", sample_log)
        assert filtered_log == expected_clean_log
