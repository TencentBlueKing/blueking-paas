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
import io
import os
import re
from dataclasses import dataclass
from typing import Optional

from blue_krill.data_types.enum import StructuredEnum


class MatchType(int, StructuredEnum):
    Unknown = 0
    Excat = 1
    Prefix = 2
    Suffix = 3
    Regexp = 4


@dataclass
class Pattern:
    """Pattern defines a single regexp used to filter file paths.

    See also: https://github.com/moby/moby/blob/HEAD/vendor/github.com/moby/patternmatcher/patternmatcher.go#L284
    """

    cleaned_pattern: str
    match_type: int = MatchType.Unknown
    regexp: Optional[re.Pattern] = None

    def match(self, path: str) -> bool:
        if self.match_type is MatchType.Unknown:
            self.compile(os.sep)

        if self.match_type == MatchType.Excat:
            return path == self.cleaned_pattern
        elif self.match_type == MatchType.Prefix:
            # strip trailing **
            return path.startswith(self.cleaned_pattern[: len(self.cleaned_pattern) - 2])
        elif self.match_type == MatchType.Suffix:
            # strip leading **
            suffix = self.cleaned_pattern[2:]
            if path.endswith(suffix):
                return True
            return suffix[0] == os.sep and path == suffix[1:]
        elif self.match_type == MatchType.Regexp:
            assert self.regexp, "match_type is Regexp, but regexp is None"
            return bool(self.regexp.match(path))
        return False

    def compile(self, sl: str):  # noqa: C901
        reg_str = "^"
        pattern = self.cleaned_pattern
        esc_sl = sl
        if esc_sl == "\\":
            esc_sl += "\\"

        self.match_type = MatchType.Excat
        scan = Scanner(pattern)
        i = 0
        while not scan.is_eof():
            ch = scan.next()
            if ch == "*":
                if scan.peek() == "*":
                    # is some flavor of "**"
                    scan.next()
                    # Treat **/ as ** so eat the "/"
                    if scan.peek() == sl:
                        scan.next()
                    if scan.is_eof():
                        # is "**EOF" - to align with .gitignore just accept all
                        if self.match_type == MatchType.Excat:
                            self.match_type = MatchType.Prefix
                        else:
                            reg_str += ".*"
                            self.match_type = MatchType.Regexp
                    else:
                        # is "**"
                        # Note that this allows for any # of /'s (even 0) because
                        # the .* will eat everything, even /'s
                        reg_str += "(.*" + esc_sl + ")?"
                        self.match_type = MatchType.Regexp
                    if i == 0:
                        self.match_type = MatchType.Suffix
                else:
                    reg_str += "[^" + esc_sl + "]*"
                    self.match_type = MatchType.Regexp
            elif ch == "?":
                # "?" is any char except "/"
                reg_str += "[^" + esc_sl + "]"
                self.match_type = MatchType.Regexp
            elif should_escape(ch):
                # Escape some regexp special chars that have no meaning in golang's filepath.Match
                reg_str += "\\" + ch
            elif ch == "\\":
                if sl == "\\":
                    # On windows map "\" to "\\", meaning an escaped backslash,
                    # and then just continue because filepath.Match on
                    # Windows doesn't allow escaping at all
                    reg_str += esc_sl
                    i += 1
                    continue
                if not scan.is_eof():
                    reg_str += "\\" + scan.next()
                    self.match_type = MatchType.Regexp
                else:
                    reg_str += "\\"
            elif ch == "[" or ch == "]":
                reg_str += ch
                self.match_type = MatchType.Regexp
            else:
                reg_str += ch
            i += 1
        if self.match_type != MatchType.Regexp:
            return
        reg_str += "$"
        self.regexp = re.compile(reg_str)
        return


def should_escape(ch: str) -> bool:
    return ch in ".+()|{}$"


class Scanner:
    """Scanner implements the minimum behavior of golang text.Scanner"""

    EOF = ""

    def __init__(self, content):
        self._buffer = io.StringIO(content)
        self.ch: Optional[str] = None

    def peek(self) -> str:
        """Peek returns the next Unicode character in the source without advancing the scanner.
        returns EOF if the scanner's position is at the last character of the source.
        """
        if self.ch is None:
            self.ch = self._next()
        return self.ch

    def next(self):
        """Next reads and returns the next Unicode character.
        It returns EOF at the end of the source.
        """
        ch = self.peek()
        if ch != self.EOF:
            self.ch = self._next()
        return ch

    def is_eof(self) -> bool:
        return self.peek() == self.EOF

    def _next(self):
        return self._buffer.read(1)
