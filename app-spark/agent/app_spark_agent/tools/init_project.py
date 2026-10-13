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

"""模型侧的 init_project：真要开始写代码时，由模型自己从模板建出 Python 项目。

什么时候建、叫什么名字交给模型，文件内容交给程序：pyproject.toml 里 uvicorn 的版本钉死、
uv.lock 与模板逐字一致，这些是启动器和离线安装依赖的东西，不能指望模型照着抄对。
"""

import re
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from app_spark_agent import settings
from app_spark_agent.utils import write_atomic

PROJECT_FILES = ("pyproject.toml", "uv.lock")

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


class InitProjectResult(BaseModel):
    """init_project 工具返回给模型的结构。

    :param status: created 已建好；exists pyproject.toml 已在，未做任何改动；invalid_name 名字不可用，
        未做任何改动。
    :param name: 写进 pyproject.toml 的项目名，即规范化之后的名字。
    :param detail: exists 或 invalid_name 的原因；created 时说明是否顶掉了一份孤立的 uv.lock。
    """

    status: Literal["created", "exists", "invalid_name"]
    name: str | None = None
    detail: str = ""


class ProjectInitializer:
    """Write the platform's project template into one workspace, under a name the model picks.

    :param template: Directory holding the template files; settings.APP_TEMPLATE_DIR by default.
    """

    def __init__(self, workspace: Path, template: Path | None = None) -> None:
        self.workspace = workspace
        self.template = settings.APP_TEMPLATE_DIR if template is None else template

    def init(self, raw_name: str) -> InitProjectResult:
        """Write the template under raw_name, when the workspace has no pyproject.toml.

        Every outcome is folded into the result instead of raised: raising out of a tool ends
        the turn, while the model can simply pick another name.
        """
        name = self.normalize_name(raw_name)
        if name is None:
            return InitProjectResult(
                status="invalid_name",
                detail=(
                    f"{raw_name!r} cannot be used as a project name. Use at most {PROJECT_NAME_MAX_LENGTH} "
                    "lowercase ASCII letters, digits and hyphens, for example `todo-board`."
                ),
            )

        # 只看 pyproject.toml，与 launch 判「还没有项目」的条件（project_env.NO_PROJECT_DETAIL）一致，
        # 否则两边会把模型互相推给对方。有 pyproject.toml 就永不覆盖：只缺 uv.lock 时 uv add / uv sync
        # 会就地补锁，这里补上一份模板锁反而造出一对互不匹配的文件。
        if (self.workspace / "pyproject.toml").exists():
            return InitProjectResult(status="exists", detail=EXISTS_DETAIL)

        # 反过来只剩 uv.lock 时，uv 什么也做不了（uv add 直接报找不到 pyproject.toml），而提示词又
        # 禁止模型手写或手改这两个文件。两个文件都按模板重写，写出来的仍是配套的一对。
        replaced_lock = (self.workspace / "uv.lock").exists()
        for filename, text in self.render(name).items():
            write_atomic(self.workspace / filename, text.encode("utf-8"))
        return InitProjectResult(status="created", name=name, detail=REPLACED_LOCK_DETAIL if replaced_lock else "")

    @staticmethod
    def normalize_name(raw: str) -> str | None:
        """Return raw in the normalized form uv records in uv.lock, or None when it has no such form.

        Runs of whitespace, '-', '_' and '.' become one hyphen, and letters become lowercase,
        so "Todo_Board" becomes "todo-board". None means nothing usable is left, or what is left
        is not ASCII letters, digits and hyphens.
        """
        name = re.sub(r"[\s._-]+", "-", raw.strip()).lower().strip("-")
        if len(name) > PROJECT_NAME_MAX_LENGTH or not _PROJECT_NAME_PATTERN.fullmatch(name):
            return None
        return name

    def render(self, name: str) -> dict[str, str]:
        """Return the template's project files, keyed by file name, with the project renamed to name.

        Both files are renamed in step. uv.lock records the project's own name too, and a lock whose
        name disagrees with pyproject.toml is stale: uv would re-resolve it over the network instead
        of installing the locked versions from the warmed cache.

        :param name: An already normalized project name.
        """
        texts = {filename: (self.template / filename).read_text(encoding="utf-8") for filename in PROJECT_FILES}
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


def build_init_project_tool(workspace: Path) -> Callable[[str], InitProjectResult]:
    """Return the init_project tool bound to workspace, as the plain function the harness registers.

    Name and docstring are what the model sees. The function blocks on file writes, which the
    harness runs in a worker thread for a synchronous tool.
    """
    initializer = ProjectInitializer(workspace)

    def init_project(name: str) -> InitProjectResult:
        """Create the Python project for this app from the platform's template.

        Call this once, before writing the application's first file. It writes `pyproject.toml`
        and `uv.lock` at the workspace root, with the starting dependencies already locked.
        Does nothing when `pyproject.toml` already exists; a `uv.lock` left without one is replaced.

        :param name: A short name for the app in lowercase ASCII letters, digits and hyphens,
            for example `todo-board`. Spaces, underscores and dots become hyphens.
        """
        return initializer.init(name)

    return init_project
