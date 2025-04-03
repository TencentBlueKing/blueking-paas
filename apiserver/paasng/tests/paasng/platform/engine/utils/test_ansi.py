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

from paasng.platform.engine.utils.ansi import bell, esc, strip_ansi


def test_strip_ansi_empty_string():
    """测试空字符串应保持不变。"""
    assert strip_ansi("") == ""


def test_strip_ansi_plain_text():
    """测试没有 ANSI 转义序列的普通文本应保持不变。"""
    plain_text = "Hello, world!"
    assert strip_ansi(plain_text) == plain_text


def test_strip_ansi_color_codes():
    """测试移除基本的 ANSI 颜色代码。"""
    colored_text = f"{esc}[31mRed text{esc}[0m"
    assert strip_ansi(colored_text) == "Red text"


def test_strip_ansi_multiple_codes():
    """测试移除字符串中的多个 ANSI 代码。"""
    text = f"{esc}[1mBold{esc}[0m {esc}[32mGreen{esc}[0m {esc}[4mUnderline{esc}[0m"
    assert strip_ansi(text) == "Bold Green Underline"


def test_strip_ansi_cursor_movement():
    """测试移除光标移动代码。"""
    text = f"Line 1{esc}[1ALine 2"
    assert strip_ansi(text) == "Line 1Line 2"


def test_strip_ansi_bell_character():
    """测试移除 bell 字符。"""
    text = f"Alert{bell}Message"
    assert strip_ansi(text) == "AlertMessage"


def test_strip_ansi_csi_sequences():
    """测试移除 CSI（控制序列引导符）序列。"""
    text = f"Text{esc}[1;31;42mColored{esc}[0m"
    assert strip_ansi(text) == "TextColored"


def test_strip_ansi_osc_sequences():
    """测试移除 OSC（操作系统命令）序列。"""
    text = f"{esc}]0;Window Title{bell}Terminal content"
    assert strip_ansi(text) == "Terminal content"


def test_strip_ansi_mixed_content():
    """测试从混合内容中移除 ANSI 代码。"""
    text = f"{esc}[1mBold{esc}[0m normal {esc}[31mred{esc}[0m\nNew{esc}[ALine"
    assert strip_ansi(text) == "Bold normal red\nNewLine"


def test_strip_ansi_alternative_characters():
    """测试移除替代字符集命令。"""
    text = f"Normal{esc}(0Special{esc}(BNormal"
    assert strip_ansi(text) == "NormalSpecialNormal"


def test_strip_ansi_preserve_non_ansi_escapes():
    """测试保留非 ANSI 转义序列。"""
    text = f"Preserve{esc}xThis"
    assert strip_ansi(text) == f"Preserve{esc}xThis"


def test_strip_ansi_edge_case_unfinished_escape():
    """测试处理未完成的转义序列。"""
    text = f"Unfinished{esc}"
    assert strip_ansi(text) == "Unfinished"


def test_strip_ansi_edge_case_only_escape():
    """测试仅包含转义字符的情况。"""
    text = f"{esc}"
    assert strip_ansi(text) == ""
