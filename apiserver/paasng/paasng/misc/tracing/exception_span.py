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

"""把请求异常的诊断信息（堆栈、源码片段、局部变量）以独立事件挂到当前 OTel Span 上"""

import linecache
import logging
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import TracebackType
from typing import Any, Iterator

from opentelemetry import trace

from paasng.utils.masked_curlify import DEFAULT_SCRUBBED_FIELDS, MASKED_CONTENT

logger = logging.getLogger(__name__)

# 每帧 LOCALS 变量最多展示数
LOCALS_PREVIEW_LIMIT = 16
# 单个变量 repr 最大长度，超出尾部截断
LOCAL_VALUE_MAX_LEN = 1024
# SOURCE 片段在崩溃行上下展开的行数
SOURCE_CONTEXT_CTX = 5
# 链式异常最多展开层数（不含根异常）
CHAIN_DEPTH_LIMIT = 2
# exception.message 总长度上限
MESSAGE_MAX_LEN = 512 * 1024
# 自定义事件名，避开 SDK 标准的 `exception`
DIAGNOSTIC_EVENT_NAME = "exception.diagnostic"


@dataclass(frozen=True)
class Frame:
    """栈帧信息"""

    # 0-based，入口帧为 0，崩溃帧为 total - 1
    index: int
    function: str
    # 相对 BASE_DIR 的 posix 路径，无法计算时退化为最后两级目录
    display_path: str
    lineno: int
    # 已含 ">" 标记、行号与缩进的源码片段
    source_snippet: str
    # (name, masked_value_repr) 列表，按 name 升序
    locals: list[tuple[str, str]]


# ----------------------------- path / source helpers -----------------------------


@lru_cache(maxsize=1)
def project_root() -> Path:
    from django.conf import settings

    return Path(settings.BASE_DIR).resolve()


def resolve_filepath(filepath: str) -> Path:
    path = Path(filepath.replace("\\", "/"))
    try:
        return path.resolve()
    except OSError:
        return path


def display_path(filepath: str) -> str:
    """优先使用相对 Django BASE_DIR 的路径；无法计算时退化为最后两级目录"""
    if not filepath:
        return ""
    resolved = resolve_filepath(filepath)
    try:
        return resolved.relative_to(project_root()).as_posix()
    except ValueError:
        return "/".join(resolved.parts[-2:])


def read_file_lines(filepath: str) -> list[str] | None:
    cached = linecache.getlines(filepath)
    if cached:
        return [line.rstrip("\n\r") for line in cached]

    try:
        path = Path(filepath)
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    return None


def build_source_snippet(filepath: str, lineno: int) -> str:
    if lineno < 1 or not filepath:
        return ""

    file_lines = read_file_lines(filepath)
    if not file_lines:
        return ""

    start = max(1, lineno - SOURCE_CONTEXT_CTX)
    end = min(lineno + SOURCE_CONTEXT_CTX, len(file_lines))
    if start > end:
        return ""

    width = len(str(end))
    rendered: list[str] = []
    for line_no in range(start, end + 1):
        marker = ">" if line_no == lineno else " "
        rendered.append(f"{marker} {line_no:>{width}} | {file_lines[line_no - 1]}")
    return "\n".join(rendered)


# ----------------------------- locals helpers -----------------------------


def is_sensitive_key(key: str) -> bool:
    lk = key.lower()
    return any(part in lk for part in DEFAULT_SCRUBBED_FIELDS)


def safe_repr(value: Any) -> str:
    try:
        text = repr(value)
    except Exception:  # noqa: BLE001
        return "<Unserializable>"
    if len(text) > LOCAL_VALUE_MAX_LEN:
        return text[:LOCAL_VALUE_MAX_LEN] + "..."
    return text


def sanitize_locals(frame_locals: dict[str, Any]) -> list[tuple[str, str]]:
    """变量脱敏展示"""
    items: list[tuple[str, str]] = []
    for name, value in frame_locals.items():
        if is_sensitive_key(name):
            items.append((name, MASKED_CONTENT))
        else:
            items.append((name, safe_repr(value)))
    items.sort(key=lambda item: item[0])
    return items


# ----------------------------- frame iteration -----------------------------


def iter_frames(tb: TracebackType | None) -> Iterator[Frame]:
    """按 Python traceback 顺序遍历栈帧（入口帧在前，崩溃帧在后）"""
    index = 0
    cursor = tb
    while cursor is not None:
        frame = cursor.tb_frame
        filepath = frame.f_code.co_filename
        lineno = cursor.tb_lineno
        yield Frame(
            index=index,
            function=frame.f_code.co_name,
            display_path=display_path(filepath),
            lineno=lineno,
            source_snippet=build_source_snippet(filepath, lineno),
            locals=sanitize_locals(frame.f_locals),
        )
        cursor = cursor.tb_next
        index += 1


# ----------------------------- format helpers -----------------------------


def format_header(exception: BaseException, frames: list[Frame]) -> str:
    exc_type = type(exception).__name__
    exc_msg = str(exception)
    lines = [f"EXCEPTION: {exc_type}: {exc_msg}"]
    if frames:
        crash = frames[-1]
        lines.append(f"ORIGIN:    {crash.display_path}:{crash.lineno} in {crash.function}")
    lines.append(f"FRAMES:    {len(frames)}")
    return "\n".join(lines)


def format_frame(frame: Frame, display_index: int, total: int) -> str:
    """`display_index` 为 1-based 展示顺位；崩溃帧用 `Frame.index` 判定，与展示顺序解耦"""
    is_crash = frame.index == total - 1
    crash_marker = " (CRASH)" if is_crash else ""
    header = f"[{display_index}/{total}] {frame.display_path}:{frame.lineno} in {frame.function}{crash_marker}"

    body: list[str] = [header, "SOURCE:"]
    if frame.source_snippet:
        body.append(frame.source_snippet)
    else:
        body.append("  (source unavailable)")

    body.append("LOCALS:")
    if frame.locals:
        for name, value in frame.locals[:LOCALS_PREVIEW_LIMIT]:
            body.append(f"  {name} = {value}")
        remaining = len(frame.locals) - LOCALS_PREVIEW_LIMIT
        if remaining > 0:
            body.append(f"  ... ({remaining} more)")
    else:
        body.append("  (none)")

    return "\n".join(body)


def format_exception(exception: BaseException, tb: TracebackType | None = None) -> str:
    """
    格式化异常的堆栈信息
    """
    if tb is None:
        tb = exception.__traceback__
    frames = list(iter_frames(tb))
    parts = [format_header(exception, frames)]
    total = len(frames)
    for display_index, frame in enumerate(reversed(frames), start=1):
        parts.append(format_frame(frame, display_index, total))
    return "\n\n".join(parts)


def collect_chain(exception: BaseException) -> list[tuple[str, BaseException]]:
    """沿 __cause__ / __context__ 收集链式异常，每跳一个 (关系标签, 后继异常)；不含根异常，最多 CHAIN_DEPTH_LIMIT 跳"""
    chain: list[tuple[str, BaseException]] = []
    seen: set[int] = {id(exception)}
    current = exception
    while len(chain) < CHAIN_DEPTH_LIMIT:
        if current.__cause__ is not None:
            label = "Caused by"
            nxt: BaseException = current.__cause__
        elif current.__context__ is not None and not current.__suppress_context__:
            label = "During handling of the above exception, another exception occurred"
            nxt = current.__context__
        else:
            break
        if id(nxt) in seen:
            # 防止环
            break
        seen.add(id(nxt))
        chain.append((label, nxt))
        current = nxt
    return chain


def format_chained(exception: BaseException) -> str:
    """格式化异常的调用栈，和对应堆栈信息"""
    chain = collect_chain(exception)
    if not chain:
        return ""
    parts: list[str] = []
    for label, exc in chain:
        parts.append(f"--- {label} ---")
        parts.append(format_exception(exc))
    return "\n\n" + "\n\n".join(parts)


def truncate(message: str) -> str:
    if len(message) <= MESSAGE_MAX_LEN:
        return message
    omitted = len(message) - MESSAGE_MAX_LEN
    return message[:MESSAGE_MAX_LEN] + f"\n... (truncated, {omitted} bytes omitted)"


# ----------------------------- public API -----------------------------


def record_exception_to_span(
    exception: BaseException,
    *,
    exc_info: Any = None,
) -> None:
    """
    BKMonitor event 的 exception.message & exception.stacktrace 支持存储长文本
    """
    span = trace.get_current_span()
    if not span.is_recording():
        return

    tb = exc_info[2] if exc_info is not None else sys.exc_info()[2]
    if tb is None and exception.__traceback__ is None:
        return

    try:
        message = truncate(format_exception(exception, tb=tb) + format_chained(exception))
        span.add_event(
            DIAGNOSTIC_EVENT_NAME,
            attributes={
                "exception.type": type(exception).__name__,
                "exception.message": message,
            },
        )
    except Exception:
        logger.exception("Failed to record exception to span")
