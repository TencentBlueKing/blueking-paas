# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

"""Python 应用的运行时、启动命令和项目模板。

什么时候建、叫什么名字交给模型，文件内容交给程序：pyproject.toml 里 uvicorn 的版本钉死、
uv.lock 与模板逐字一致，这些是启动器和离线安装依赖的东西，不能指望模型照着抄对。
"""

import re
import shlex
import tomllib
from pathlib import Path

from app_spark_agent import settings
from app_spark_agent.app_arch.files import (
    AppArchErrorCode,
    FileSyncResult,
    FileSyncStatus,
    sync_text_files,
)

PYTHON_VERSION = "3.14"
PYTHON_VERSION_FILENAME = ".python-version"
PYTHON_PROJECT_FILES = ("pyproject.toml", "uv.lock")

# 模型被要求把应用导出成这个路径，预览（app_supervisor/app_spec.py）和部署（app_desc.yaml 的
# procCommand）都从这里取。settings.INSTRUCTIONS 的 App Framework 一节写着同一条约定，这两处要
# 一起改，tests/test_app_supervisor.py 守着：模型写成别的入口名，launch 和部署都会失败。
APP_IMPORT_PATH = "main:app"

# 听所有网卡，给沙箱外的预览代理和 PaaS Service 访问。判活仍只连 127.0.0.1。
APP_LISTEN_HOST = "0.0.0.0"

# 只收 PEP 503 规范化后的名字：uv 在 uv.lock 里记的就是这个形式。pyproject.toml 写成别的样子，
# uv 会判锁文件过期，新项目首次启动就得联网重新解析，模板预热的缓存也就白热了。
_PROJECT_NAME_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
PROJECT_NAME_MAX_LENGTH = 64

EXISTS_DETAIL = (
    "The workspace already has a pyproject.toml. Keep using it: add packages with "
    "`uv add` instead of creating the project again."
)

REPLACED_LOCK_DETAIL = (
    "The workspace had a uv.lock without a pyproject.toml, which uv cannot use; it was replaced "
    "together with the new pyproject.toml."
)


def render_python_version() -> str:
    """Return the runtime selector written to .python-version."""
    return f"{PYTHON_VERSION}\n"


def sync_python_version(workspace: Path) -> FileSyncResult:
    """Create or repair the Python runtime selector."""
    return sync_text_files(workspace, {PYTHON_VERSION_FILENAME: render_python_version()})


def build_uvicorn_args(port: int) -> tuple[str, ...]:
    """Return the uvicorn arguments shared by preview and deployment."""
    return (
        "-m",
        "uvicorn",
        APP_IMPORT_PATH,
        "--host",
        APP_LISTEN_HOST,
        "--port",
        str(port),
    )


def build_proc_command(port: int) -> str:
    """Return the portable deployment command equivalent to the preview command on port."""
    return shlex.join(("python", *build_uvicorn_args(port)))


def sync_python_project(
    workspace: Path,
    raw_name: str,
    template: Path | None = None,
) -> FileSyncResult:
    """Write the template under raw_name, when the workspace has no pyproject.toml.

    Every outcome is folded into the shared FileSyncResult instead of raised: raising out of a
    tool ends the turn, while the model can simply pick another name.

    :param template: Directory holding the template files; settings.APP_TEMPLATE_DIR by default.
    """
    name = normalize_project_name(raw_name)
    if name is None:
        return FileSyncResult(
            status=FileSyncStatus.FAILED,
            files=PYTHON_PROJECT_FILES,
            errcode=AppArchErrorCode.INVALID_PROJECT_NAME,
            detail=(
                f"{raw_name!r} cannot be used as a project name. Use at most {PROJECT_NAME_MAX_LENGTH} "
                "lowercase ASCII letters, digits and hyphens, for example `todo-board`."
            ),
        )

    # 只看 pyproject.toml，与 launch 判「还没有项目」的条件（project_env.NO_PROJECT_DETAIL）一致，
    # 否则两边会把模型互相推给对方。有 pyproject.toml 就永不覆盖：只缺 uv.lock 时 uv add / uv sync
    # 会就地补锁，这里补上一份模板锁反而造出一对互不匹配的文件。
    if (workspace / "pyproject.toml").exists():
        return FileSyncResult(
            status=FileSyncStatus.UNCHANGED,
            files=PYTHON_PROJECT_FILES,
            detail=EXISTS_DETAIL,
        )

    # 反过来只剩 uv.lock 时，uv 什么也做不了（uv add 直接报找不到 pyproject.toml），而提示词又
    # 禁止模型手写或手改这两个文件。两个文件都按模板重写，写出来的仍是配套的一对。
    replaced_lock = (workspace / "uv.lock").exists()
    try:
        rendered = render_python_project(name, template)
    except (KeyError, OSError, RuntimeError, ValueError) as exc:
        return FileSyncResult(
            status=FileSyncStatus.FAILED,
            files=PYTHON_PROJECT_FILES,
            errcode=AppArchErrorCode.TEMPLATE_FAILED,
            detail=f"Could not render the Python project template: {exc}",
        )
    result = sync_text_files(workspace, rendered)
    if result.status is FileSyncStatus.FAILED:
        return result

    created_detail = f"Created Python project {name}."
    detail = f"{created_detail} {REPLACED_LOCK_DETAIL}" if replaced_lock else created_detail
    return FileSyncResult(
        status=result.status,
        files=result.files,
        changed=result.changed,
        detail=detail,
    )


def normalize_project_name(raw: str) -> str | None:
    """Return raw in the normalized form uv records in uv.lock, or None when it has no such form.

    Runs of whitespace, '-', '_' and '.' become one hyphen, and letters become lowercase,
    so "Todo_Board" becomes "todo-board". None means nothing usable is left, or what is left
    is not ASCII letters, digits and hyphens.
    """
    name = re.sub(r"[\s._-]+", "-", raw.strip()).lower().strip("-")
    if len(name) > PROJECT_NAME_MAX_LENGTH or not _PROJECT_NAME_PATTERN.fullmatch(name):
        return None
    return name


def render_python_project(name: str, template: Path | None = None) -> dict[str, str]:
    """Return the template's project files, keyed by file name, with the project renamed to name.

    Both files are renamed in step. uv.lock records the project's own name too, and a lock whose
    name disagrees with pyproject.toml is stale: uv would re-resolve it over the network instead
    of installing the locked versions from the warmed cache.

    :param name: An already normalized project name.
    :param template: Directory holding the template files; settings.APP_TEMPLATE_DIR by default.
    """
    template_dir = settings.APP_TEMPLATE_DIR if template is None else template
    texts = {filename: (template_dir / filename).read_text(encoding="utf-8") for filename in PYTHON_PROJECT_FILES}
    template_name = tomllib.loads(texts["pyproject.toml"])["project"]["name"]

    # 按行替换而不是解析再写回：标准库只能读 TOML，不能写；而替换一行能保证锁文件里其余内容
    # 逐字不变，uv 才认它没过期。模板里项目名之外不能再有一行同样的 name，否则就分不清了。
    pattern = re.compile(rf'^name = "{re.escape(template_name)}"$', re.MULTILINE)
    rendered = {}
    for filename, text in texts.items():
        renamed, count = pattern.subn(f'name = "{name}"', text)
        if count != 1:
            raise RuntimeError(f"Expected the template's {filename} to name the project once, found {count}")
        rendered[filename] = renamed
    return rendered
