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

"""The workspace project's own Python environment: its uv settings and its sync.

依赖属于用户项目：pyproject.toml 与 uv.lock 在 workspace 里，随代码保存和下载；环境建在
workspace/.venv，launch 前由 uv sync 按锁文件对齐。平台只提供模板和包源。

项目由模型在真要开始写代码时用 init_project 工具（tools/init_project.py）从模板建，而不是
每轮 run 开始时自动拷：只聊天、不改文件的会话就不会因为两份模板文件而多出一次提交。
"""

import asyncio
import os
import shutil
import signal
from collections.abc import Mapping
from pathlib import Path

from app_spark_agent import settings
from app_spark_agent.app_supervisor.types import AppLaunchFailed
from app_spark_agent.utils import append_text_ignore_unwritable, killpg_ignore_absent

NO_PROJECT_DETAIL = (
    "The workspace has no pyproject.toml, so there are no dependencies to install. "
    "Create the project with the `init_project` tool, then launch again."
)

# 冷缓存下首次联网解析加下载的上限。缓存预热过的模板只要零点几秒，这个值是给模型新加了
# 依赖、要现下的那一次留的。
SYNC_TIMEOUT_SECONDS = 300.0

# 失败时交回模型的 uv 输出尾巴。uv 把真正的原因写在最后几行，全文在应用日志里。
SYNC_OUTPUT_TAIL_CHARS = 2000

# 指向 agent 自己的环境，交给项目的 uv 会出事：UV_PROJECT_ENVIRONMENT 会让 uv sync 把 agent
# 的 venv 按项目依赖「对齐」掉；VIRTUAL_ENV 是以 `uv run` 启动 agent 时留下的，只会招来
# 「与项目环境不符」的告警。
_AGENT_ENVIRONMENT_KEYS = frozenset({"VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT"})


def project_python(workspace: Path) -> Path:
    """Return the interpreter uv sync builds for the workspace project."""
    return workspace / ".venv" / "bin" / "python"


def uv_environ(source: Mapping[str, str]) -> dict[str, str]:
    """Copy source for running uv against the workspace project.

    Shared by the sync before each launch and the model's Shell, so that `uv add` in the shell
    resolves against the same index the launch installs from.
    """
    env = {
        key: value
        for key, value in source.items()
        if not key.startswith(settings.ENV_PREFIX) and key not in _AGENT_ENVIRONMENT_KEYS
    }
    env["UV_DEFAULT_INDEX"] = settings.PACKAGE_INDEX_URL

    # 沙箱里只有镜像自带的 Python。模型改了 requires-python 时，宁可当场报「找不到解释器」，
    # 也不要卡在一次注定失败的下载上。
    env["UV_PYTHON_DOWNLOADS"] = "never"
    return env


async def sync_project_environment(workspace: Path, log_path: Path) -> None:
    """Bring workspace/.venv in line with the project's lock file, installing what is missing.

    The uv output is appended to log_path, where read_app_log finds it next to the
    application's own output.

    :raises AppLaunchFailed: The workspace has no project yet, or uv is missing, timed out, or
        could not install the dependencies.
    """
    # uv 自己也会报找不到 pyproject.toml，但不会告诉模型该用哪个工具去建。
    if not (workspace / "pyproject.toml").is_file():
        raise AppLaunchFailed(NO_PROJECT_DETAIL)

    uv = shutil.which("uv")
    if uv is None:
        raise AppLaunchFailed(
            "The platform's `uv` command is missing, so the project's dependencies cannot be installed. "
            "The workspace code did not cause this and cannot fix it; report it to the user."
        )

    try:
        # 不加 --frozen / --locked：模型手改 pyproject.toml 却没重新锁时，就地重锁比报错让它再跑一遍
        # 更直接。uv.lock 因此可能在 launch 时被改写，它本来就是项目文件，会随这一轮一起保存。
        process = await asyncio.create_subprocess_exec(
            uv,
            "sync",
            "--no-dev",
            cwd=workspace,
            env=uv_environ(os.environ),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            # 独立进程组：超时或被取消时，连 uv 拉起的构建后端一起杀掉。
            start_new_session=True,
        )
    except OSError as exc:
        raise AppLaunchFailed(f"`uv sync` could not be started: {exc}") from exc

    try:
        output, _ = await asyncio.wait_for(process.communicate(), SYNC_TIMEOUT_SECONDS)
    except TimeoutError:
        raise AppLaunchFailed(
            f"Installing the project's dependencies did not finish within {SYNC_TIMEOUT_SECONDS:.0f}s. "
            "The package index may be unreachable from the sandbox."
        ) from None
    finally:
        # 超时之外，所在的 launch 被取消也走这里。不收掉就会留下一个没人等的 uv。
        if process.returncode is None:
            killpg_ignore_absent(process.pid, signal.SIGKILL)
            await process.wait()

    # 记录日志，忽略日志记录失败的情况
    text = output.decode(errors="replace")
    await asyncio.to_thread(append_text_ignore_unwritable, log_path, text)
    if process.returncode != 0:
        raise AppLaunchFailed(
            f"Installing the project's dependencies failed (`uv sync` exited with {process.returncode}):\n"
            f"{text[-SYNC_OUTPUT_TAIL_CHARS:].strip()}"
        )
