# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

"""就绪探针：什么算「应用在听」，它比纯 TCP 严在哪，以及它不该误杀什么。"""

import asyncio
import socket
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app_spark_agent.app_supervisor.process import http_get_answers, tcp_port_is_open


class _StatusHandler(BaseHTTPRequestHandler):
    """Answer every request with whatever status the server was set up to give, after a delay."""

    def do_GET(self) -> None:
        time.sleep(self.server.reply_delay)  # type: ignore[attr-defined]
        self.send_response(self.server.reply_status)  # type: ignore[attr-defined]
        self.end_headers()

    def log_message(self, *_args: object) -> None:
        """Keep the test output free of one access log line per probe."""


@contextmanager
def serving_status(status: int, *, delay: float = 0.0) -> Iterator[int]:
    """Run a throwaway HTTP server that answers every GET with status, and yield its port."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StatusHandler)
    server.reply_status = status  # type: ignore[attr-defined]
    server.reply_delay = delay  # type: ignore[attr-defined]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield int(server.server_address[1])
    finally:
        server.shutdown()
        server.server_close()


@contextmanager
def hold_port_open() -> Iterator[int]:
    """Hold a port open without ever speaking HTTP on it, and yield the port."""
    with socket.socket() as squatter:
        squatter.bind(("127.0.0.1", 0))
        squatter.listen(1)
        yield int(squatter.getsockname()[1])


def find_unused_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


@pytest.mark.parametrize("status", [200, 404, 500])
async def test_any_http_answer_counts_as_listening(status: int) -> None:
    """探针只问「这个端口上有没有一个 HTTP 服务」。返回什么状态码是应用自己的事。"""
    with serving_status(status) as port:
        assert await http_get_answers(port) is True


async def test_a_closed_port_is_not_listening() -> None:
    assert await http_get_answers(find_unused_port()) is False


async def test_a_port_that_is_held_but_never_answers_is_not_listening() -> None:
    """这正是换掉纯 TCP 探针的理由：绑上端口不等于能处理请求。"""
    with hold_port_open() as port:
        assert tcp_port_is_open(port) is True
        assert await http_get_answers(port, read_timeout=0.2) is False


async def test_an_application_slower_than_the_connect_budget_still_counts_as_listening() -> None:
    """建连和应答的预算是分开的。合在一起给 0.2 秒，会把正常应用判成掉听再被重启。"""
    with serving_status(200, delay=0.5) as port:
        assert await http_get_answers(port) is True


async def test_the_probe_does_not_block_the_event_loop() -> None:
    """探针每 0.5 秒跑一次；同步实现会在应用变慢时把进行中的 /runs SSE 一起堵住。"""
    ticks = 0

    async def count_ticks() -> None:
        nonlocal ticks
        while True:
            await asyncio.sleep(0.01)
            ticks += 1

    ticker = asyncio.create_task(count_ticks())
    try:
        with hold_port_open() as port:
            assert await http_get_answers(port, read_timeout=0.5) is False
    finally:
        ticker.cancel()

    # 探针等了 0.5 秒。事件循环没被占住的话，10ms 的心跳在这段时间里应该跑了很多次。
    assert ticks > 10
