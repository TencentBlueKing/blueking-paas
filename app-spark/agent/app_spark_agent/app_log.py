"""读用户应用的约定日志。

这里的应用是用户用自然语言编出来、跑在沙箱里的那个服务，不是 Agent 进程。
只读 APP_LOG_PATH 这一条，不接受路径参数，单次不超过尾部 8KB。
后续会把该服务的 stdout/stderr 接到同一文件。
"""

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from app_spark_agent import settings
from app_spark_agent.masking import mask_text

NO_LOG_MESSAGE = "无日志"
READ_ERROR_PREFIX = "读取失败"


class AppLogReadResult(BaseModel):
    """日志工具返回给模型的结构，方便按字段消费而不是猜一段纯文本。

    :param status: ok 读到了正文；empty 文件不存在或长度为 0；error 读失败。
    :param content: 正文，或「无日志」/「读取失败: …」。
    :param truncated: 是否只保留了文件尾部。
    :param byte_length: 从文件取出的字节数，保证 <= APP_LOG_MAX_BYTES。
    """

    status: Literal["ok", "empty", "error"]
    content: str
    truncated: bool = False
    byte_length: int = Field(default=0, ge=0)


class AppLogReader:
    """只读用户应用的约定日志文件。构造时就拒绝落在 workspace / state 里的路径。"""

    def __init__(
        self,
        path: Path,
        *,
        max_bytes: int = settings.APP_LOG_MAX_BYTES,
        workspace: Path | None = None,
        state_dir: Path | None = None,
    ) -> None:
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        self._configured = path.expanduser()
        self.path = self._configured.resolve()
        self.max_bytes = max_bytes
        self._workspace = workspace.expanduser().resolve() if workspace is not None else None
        self._state_dir = state_dir.expanduser().resolve() if state_dir is not None else None
        self._reject_if_inside_protected(self.path)

    def read(self) -> AppLogReadResult:
        """读约定文件的尾部。任何失败都折成结构体，不向上抛。"""
        try:
            # 每次读都重新解析：构造后路径被换成软链时，不能沿用当时的目标。
            resolved = self._configured.resolve()
            self._reject_if_inside_protected(resolved)
            if resolved != self.path:
                return self._error("APP_LOG_PATH resolved to a different file")

            # 缺文件当无日志；存在但不是普通文件才报错。
            if not self.path.exists() or not self.path.is_file():
                if self.path.exists() and not self.path.is_file():
                    return self._error(f"{self.path.name} is not a regular file")
                return AppLogReadResult(status="empty", content=NO_LOG_MESSAGE)

            size = self.path.stat().st_size
            if size == 0:
                return AppLogReadResult(status="empty", content=NO_LOG_MESSAGE)

            truncated = size > self.max_bytes
            take = min(size, self.max_bytes)
            raw = self._read_tail(take, truncated)
        except (OSError, ValueError) as exc:
            return self._error(str(exc))

        return AppLogReadResult(
            status="ok",
            content=mask_text(raw.decode("utf-8", errors="replace")),
            truncated=truncated,
            byte_length=len(raw),
        )

    def _read_tail(self, take: int, truncated: bool) -> bytes:
        """打开约定路径，读尾部 take 字节。"""

        # resolve 之后、open 之前被换成软链时，O_NOFOLLOW 不跟着走。
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW

        fd = os.open(self.path, flags)
        with os.fdopen(fd, "rb") as handle:
            if truncated:
                handle.seek(-take, 2)
            return handle.read(take)

    def _reject_if_inside_protected(self, path: Path) -> None:
        """拒绝落在 workspace / state 里的路径。"""
        if self._workspace is not None and _is_inside(path, self._workspace):
            raise ValueError("APP_LOG_PATH must be outside the workspace")

        if self._state_dir is not None and _is_inside(path, self._state_dir):
            raise ValueError("APP_LOG_PATH must be outside the state directory")

    def _error(self, reason: str) -> AppLogReadResult:
        """把失败折成 error 结构体。"""
        return AppLogReadResult(status="error", content=f"{READ_ERROR_PREFIX}: {reason}")


def resolve_app_log_path(*, workspace: Path, state_dir: Path | None = None) -> Path:
    """把当前配置的约定路径解析成绝对路径，并拒绝落在 workspace / state 内。"""
    return AppLogReader(
        Path(settings.APP_LOG_PATH),
        workspace=workspace,
        state_dir=state_dir,
    ).path


def _is_inside(path: Path, directory: Path) -> bool:
    resolved = path.expanduser().resolve()
    root = directory.expanduser().resolve()
    return resolved == root or root in resolved.parents
