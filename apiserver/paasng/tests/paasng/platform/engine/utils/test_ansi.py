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

from paasng.platform.engine.utils.ansi import bell, esc, strip_ansi


@pytest.mark.parametrize(
    ("input_text", "expected_output", "description"),
    [
        ("", "", "空字符串应保持不变"),
        ("Hello, world!", "Hello, world!", "没有 ANSI 转义序列的普通文本应保持不变"),
        (f"{esc}[31mRed text{esc}[0m", "Red text", "移除基本的 ANSI 颜色代码"),
        (
            f"{esc}[1mBold{esc}[0m {esc}[32mGreen{esc}[0m {esc}[4mUnderline{esc}[0m",
            "Bold Green Underline",
            "移除字符串中的多个 ANSI 代码",
        ),
        (f"Line 1{esc}[1ALine 2", "Line 1Line 2", "移除光标移动代码"),
        (f"Alert{bell}Message", "AlertMessage", "移除 bell 字符"),
        (f"Text{esc}[1;31;42mColored{esc}[0m", "TextColored", "移除 CSI（控制序列引导符）序列"),
        (f"{esc}]0;Window Title{bell}Terminal content", "Terminal content", "移除 OSC（操作系统命令）序列"),
        (
            f"{esc}[1mBold{esc}[0m normal {esc}[31mred{esc}[0m\nNew{esc}[ALine",
            "Bold normal red\nNewLine",
            "从混合内容中移除 ANSI 代码",
        ),
        (f"Normal{esc}(0Special{esc}(BNormal", "NormalSpecialNormal", "移除替代字符集命令"),
        (f"Preserve{esc}xThis", f"Preserve{esc}xThis", "保留非 ANSI 转义序列"),
        (f"Unfinished{esc}", "Unfinished", "处理未完成的转义序列"),
        (f"{esc}", "", "仅包含转义字符的情况"),
    ],
)
def test_strip_ansi(input_text, expected_output, description):
    """测试 strip_ansi 函数在各种情况下的表现。"""
    assert strip_ansi(input_text) == expected_output
