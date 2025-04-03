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

from enum import IntEnum


class ANSIParserState(IntEnum):
    DEFAULT = 0
    ESCAPED = 1
    IN_CSI = 2
    START_OSC = 3
    IN_OSC = 4
    IGNORE_NEXT = 5


# 特殊字符常量
esc, bell = "\x1b", "\x07"


def strip_ansi(text: str) -> str:  # noqa: C901, PLR0912
    """
    Strip ANSI escape sequences from a string.

    see also: https://en.wikipedia.org/wiki/ANSI_escape_code#CSI_codes

    This function logic is rewritten from https://github.com/gabe565/ansi2txt/blob/main/pkg/ansi2txt/writer.go
    """

    result = []
    state = ANSIParserState.DEFAULT

    for char in text:
        if state == ANSIParserState.DEFAULT:
            if char == esc:
                state = ANSIParserState.ESCAPED
            elif char != bell:
                result.append(char)

        elif state == ANSIParserState.ESCAPED:
            if char == "[":
                state = ANSIParserState.IN_CSI
            elif char == "]":
                state = ANSIParserState.START_OSC
            elif char in {"%", "(", ")", "0", "3", "5", "6", "#"}:
                state = ANSIParserState.IGNORE_NEXT
            elif char in {
                bell,
                "A",
                "B",
                "C",
                "D",
                "E",
                "H",
                "I",
                "J",
                "K",
                "M",
                "N",
                "O",
                "S",
                "T",
                "Z",
                "U",
                "c",
                "s",
                "u",
                "1",
                "2",
                "7",
                "8",
                "<",
                "=",
                ">",
            }:
                state = ANSIParserState.DEFAULT
            else:
                result.append(esc + char)
                state = ANSIParserState.DEFAULT

        elif state == ANSIParserState.IN_CSI:
            if char not in {";", "?", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}:
                state = ANSIParserState.DEFAULT

        elif state == ANSIParserState.START_OSC:
            if char in {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}:
                state = ANSIParserState.IN_OSC
            else:
                state = ANSIParserState.DEFAULT

        elif state == ANSIParserState.IN_OSC:
            if char == bell:
                state = ANSIParserState.DEFAULT
            elif char == esc:
                state = ANSIParserState.IGNORE_NEXT

        elif state == ANSIParserState.IGNORE_NEXT:
            state = ANSIParserState.DEFAULT

    return "".join(result)
