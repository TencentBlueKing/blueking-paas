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


def strip_ansi(text) -> str:  # noqa: C901, PLR0912
    """
    Remove ANSI escape sequences from string.
    """

    # 定义状态常量
    (state_default, state_escaped, state_in_csi, state_start_osc, state_in_osc, state_ignore_next) = range(6)

    # 特殊字符常量
    esc, bell = "\x1b", "\x07"

    result = []
    state = state_default

    for char in text:
        if state == state_default:
            if char == esc:
                state = state_escaped
            elif char != bell:
                result.append(char)

        elif state == state_escaped:
            if char == "[":
                state = state_in_csi
            elif char == "]":
                state = state_start_osc
            elif char in "%()0356#":
                state = state_ignore_next
            elif char in (bell + "ABCDEHIJKMNOSTZU" + "csu" + "1278<=>"):
                state = state_default
            else:
                result.append(esc + char)
                state = state_default

        elif state == state_in_csi:
            if char not in ";?0123456789":
                state = state_default

        elif state == state_start_osc:
            if char in "0123456789":
                state = state_in_osc
            else:
                state = state_default

        elif state == state_in_osc:
            if char == bell:
                state = state_default
            elif char == esc:
                state = state_ignore_next

        elif state == state_ignore_next:
            state = state_default

    return "".join(result)
