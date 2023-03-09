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
from unittest import mock

import pytest

from paas_wl.release_controller.builder.infras import BuildProcedure
from paas_wl.utils.stream import ConsoleStream, MixedStream, Stream

pytestmark = pytest.mark.django_db(databases=['default', 'workloads'])


class TestStream:
    def test_cleanup_message(self):
        message_list = ["error\x1b[1G error\x1b[1G", "normal, normal", "\x1b [1G", "中文"]
        output_list = ["error error", "normal, normal", "\x1b [1G", "中文"]
        for i, message in enumerate(message_list):
            assert Stream.cleanup_message(message) == output_list[i], "输出与预期不一致"


class TestConsoleStream:
    def test_console_stream_stdout(self):
        line = []
        with mock.patch("sys.stdout") as stdout:
            stdout.write.side_effect = lambda text: line.append(text)
            ConsoleStream.write_title("write_title")
            ConsoleStream.write_message("write_message")
        assert "".join(line) == "write_title\nwrite_message\n", "输出与预期不一致"

    def test_console_stream_stderr(self):
        line = []
        with mock.patch("sys.stderr") as stderr:
            stderr.write.side_effect = lambda text: line.append(text)
            ConsoleStream.write_title("write_title")
            ConsoleStream.write_message("write_message", "STDERR")
        assert "".join(line) == "write_message\n", "输出与预期不一致"


class TestMixStream:
    def test_write_message(self, build_proc):
        bps = MixedStream(build_proc, None)
        bps.write_message("这是一段文字信息")
        bps.write_message("write \n message test")
        assert build_proc.output_stream.lines.count() == 2, "日志数量不一致"
        assert list(build_proc.output_stream.lines.values_list("line", flat=True)) == [
            "这是一段文字信息\n",
            "write \n message test\n",
        ], "日志内容与预期不一致"

    def test_write_title(self, build_proc):
        bps = MixedStream(build_proc, None)
        bps.write_title("测试标题")
        assert build_proc.output_stream.lines.count() == 0, "标题内容写进了日志！"


class TestBuildProcedure:
    def test_without_exception(self):
        line = []
        with mock.patch("sys.stdout") as stdout:
            stdout.write.side_effect = lambda text: line.append(text)
            with BuildProcedure(ConsoleStream(), "这是标题", prefix="这是前缀: "):
                pass
            assert "".join(line).startswith("这是前缀: 这是标题\n"), "输出与预期不一致"

    def test_with_exception(self):
        line = []
        with mock.patch("sys.stdout") as stdout, pytest.raises(Exception):
            stdout.write.side_effect = lambda text: line.append(text)
            with BuildProcedure(ConsoleStream(), "这是标题"):
                raise Exception("异常")
            assert "".join(line)[0] == "步骤 [这是标题] 出错了，请稍候重试。\n", "输出与预期不一致"
