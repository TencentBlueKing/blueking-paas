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

from paasng.misc.tools.smart_app.output import ConsoleStream, RedisWithModelStream, get_all_logs

pytestmark = pytest.mark.django_db


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
    def test_write_message(self, smart_build):
        log_stream = RedisWithModelStream(smart_build.stream, mock.MagicMock())
        log_stream.write_message("message")
        log_stream.write_message("write \n message test")
        assert smart_build.stream.lines.count() == 2
        assert list(smart_build.stream.lines.values_list("line", flat=True)) == [
            "message\n",
            "write \n message test\n",
        ]

    def test_write_title(self, smart_build):
        RedisWithModelStream(smart_build, mock.MagicMock()).write_title("title")
        assert smart_build.stream.lines.count() == 0, "title should not be saved"


def test_get_all_logs(smart_build):
    logs = get_all_logs(smart_build)
    assert logs.strip() == ""
