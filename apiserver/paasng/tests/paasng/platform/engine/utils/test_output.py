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

from unittest import mock

import pytest

from paasng.platform.engine.utils.output import ConsoleStream, ModelStream, RedisWithModelStream

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestModelStream:
    def test_cleanup_message(self):
        message_list = ["error\x1b[1G error\x1b[1G", "normal, normal", "\x1b [1G", "中文"]
        output_list = ["error error", "normal, normal", "\x1b [1G", "中文"]
        for s, ret in zip(message_list, output_list):
            assert ModelStream.cleanup_message(s) == ret


class TestConsoleStream:
    def test_console_stream_stdout(self):
        line = []
        with mock.patch("sys.stdout") as stdout:
            stdout.write.side_effect = lambda text: line.append(text)
            ConsoleStream().write_title("write_title")
            ConsoleStream().write_message("write_message")

        assert "".join(line) == "[TITLE]: write_title\nwrite_message\n"

    def test_console_stream_stderr(self):
        line = []
        with mock.patch("sys.stderr") as stderr:
            stderr.write.side_effect = lambda text: line.append(text)
            ConsoleStream().write_title("write_title")
            ConsoleStream().write_message("write_message", "STDERR")

        assert "".join(line) == "write_message\n"


class TestMixStream:
    def test_write_message(self, build_proc):
        bps = RedisWithModelStream(build_proc.output_stream, mock.MagicMock())
        bps.write_message("message")
        bps.write_message("write \n message test")
        assert build_proc.output_stream.lines.count() == 2
        assert list(build_proc.output_stream.lines.values_list("line", flat=True)) == [
            "message\n",
            "write \n message test\n",
        ]

    def test_write_title(self, build_proc):
        RedisWithModelStream(build_proc, mock.MagicMock()).write_title("title")
        assert build_proc.output_stream.lines.count() == 0, "title should not be saved"
