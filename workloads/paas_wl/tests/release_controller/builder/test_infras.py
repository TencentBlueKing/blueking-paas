# -*- coding: utf-8 -*-
from unittest import mock

import pytest
from django.test import TestCase

from paas_wl.release_controller.builder.infras import BuildProcedure
from paas_wl.utils.stream import ConsoleStream, MixedStream, Stream
from tests.utils.app import random_fake_app
from tests.utils.build_process import random_fake_bp


class TestStream(TestCase):
    def test_cleanup_message(self):
        message_list = ["error\x1b[1G error\x1b[1G", "normal, normal", "\x1b [1G", "中文"]
        output_list = ["error error", "normal, normal", "\x1b [1G", "中文"]
        for i, message in enumerate(message_list):
            assert Stream.cleanup_message(message) == output_list[i], "输出与预期不一致"


class TestConsoleStream(TestCase):
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


class TestMixStream(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.app = random_fake_app()
        self.bp = random_fake_bp(self.app)
        # StreamChannel 的测试由 StreamChannel 保证
        self.bps = MixedStream(self.bp, None)

    def test_write_message(self):
        self.bps.write_message("这是一段文字信息")
        self.bps.write_message("write \n message test")
        assert self.bp.output_stream.lines.count() == 2, "日志数量不一致"
        assert list(self.bp.output_stream.lines.values_list("line", flat=True)) == [
            "这是一段文字信息\n",
            "write \n message test\n",
        ], "日志内容与预期不一致"

    def test_write_title(self):
        self.bps.write_title("测试标题")
        assert self.bp.output_stream.lines.count() == 0, "标题内容写进了日志！"


class TestBuildProcedure(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.app = random_fake_app()
        self.bp = random_fake_bp(self.app)
        # StreamChannel 的测试由 StreamChannel 保证
        self.bps = MixedStream(self.bp, None)

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
