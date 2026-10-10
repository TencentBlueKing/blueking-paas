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

"""项目自己的环境：交给 uv 的环境变量、launch 前的 uv sync，以及模板本身。

从模板建项目在 tests/tools/test_init_project.py。uv sync 用 PATH 上的一个假 uv 脚本来验：要验的
是真子进程的超时、退出码和输出去向，而真 uv 要么得联网，要么得依赖本机缓存里恰好有什么。真 uv 的
那条路径在镜像里端到端验。
"""

import os
import re
import stat
import tomllib
from pathlib import Path

import pytest

from app_spark_agent import settings
from app_spark_agent.app_supervisor import AppLaunchFailed, sync_project_environment, uv_environ
from app_spark_agent.app_supervisor import project_env as project_env_mod

TEMPLATE = Path(__file__).parents[1] / "app-template"


def dependency_names(pyproject: Path) -> set[str]:
    # "jinja2>=3.1.6,<4.0.0" -> "jinja2"
    dependencies = tomllib.loads(pyproject.read_text())["project"]["dependencies"]
    return {re.split(r"[\s<>=!~;\[]", dep, maxsplit=1)[0].lower() for dep in dependencies}


class TestTemplate:
    def test_instructions_name_exactly_the_templates_dependencies(self) -> None:
        """提示词说新项目里有什么，模板里就得有什么：多写一个模型会 import 失败，少写一个它不会用。"""
        promised = re.search(r"starts with exactly:\s*([^;]+);", settings.INSTRUCTIONS)

        assert promised is not None
        assert {name.strip() for name in promised.group(1).split(",")} == dependency_names(TEMPLATE / "pyproject.toml")

    def test_uvicorn_is_pinned_to_one_version(self) -> None:
        """启动命令是平台拼的，uvicorn 的命令行在不同版本间会变，所以只认一个版本。"""
        dependencies = tomllib.loads((TEMPLATE / "pyproject.toml").read_text())["project"]["dependencies"]

        assert [dep for dep in dependencies if dep.startswith("uvicorn")] == ["uvicorn==0.54.0"]

    def test_the_lock_was_resolved_against_the_default_index(self) -> None:
        """对着别的包源锁出来的 uv.lock，在缺省包源下会被 uv 判为过期，新项目首次启动就得联网重锁。"""
        lock = tomllib.loads((TEMPLATE / "uv.lock").read_text())
        registries = {
            package["source"]["registry"] for package in lock["package"] if "registry" in package.get("source", {})
        }

        assert registries == {settings.DEFAULT_PACKAGE_INDEX_URL}


class TestUvEnviron:
    def test_points_uv_at_the_configured_index_and_away_from_the_agents_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "PACKAGE_INDEX_URL", "https://pypi.example.com/simple")
        source = {
            "PATH": "/usr/bin",
            "APP_SPARK_AGENT_RUNTIME_TOKEN": "secret",
            "VIRTUAL_ENV": "/app/agent/.venv",
            "UV_PROJECT_ENVIRONMENT": "/app/agent/.venv",
        }

        env = uv_environ(source)

        assert env == {
            "PATH": "/usr/bin",
            "UV_DEFAULT_INDEX": "https://pypi.example.com/simple",
            "UV_PYTHON_DOWNLOADS": "never",
        }


def install_fake_uv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, body: str) -> None:
    """Put a shell script named uv first on PATH. body runs with the uv arguments as "$@"."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = bin_dir / "uv"
    script.write_text(f"#!/bin/sh\n{body}\n")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}/usr/bin{os.pathsep}/bin")


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """A workspace whose project has been created; the fake uv never reads the file."""
    path = tmp_path / "workspace"
    path.mkdir()
    (path / "pyproject.toml").write_text('[project]\nname = "todo-board"\n')
    return path


class TestSyncProjectEnvironment:
    async def test_a_workspace_without_a_project_points_the_model_at_init_project(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, workspace: Path
    ) -> None:
        """uv 自己的报错只说找不到 pyproject.toml，不告诉模型该用哪个工具去建。"""
        install_fake_uv(monkeypatch, tmp_path, "echo uv-was-run")
        (workspace / "pyproject.toml").unlink()
        log = tmp_path / "app.log"

        with pytest.raises(AppLaunchFailed, match="`init_project` tool"):
            await sync_project_environment(workspace, log)
        assert not log.exists()

    async def test_runs_uv_sync_in_the_workspace_and_logs_its_output(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, workspace: Path
    ) -> None:
        monkeypatch.setattr(settings, "PACKAGE_INDEX_URL", "https://pypi.example.com/simple")
        install_fake_uv(monkeypatch, tmp_path, 'echo "args=$* cwd=$(pwd) index=$UV_DEFAULT_INDEX"')
        log = tmp_path / "app.log"

        await sync_project_environment(workspace, log)

        assert log.read_text() == f"args=sync --no-dev cwd={workspace} index=https://pypi.example.com/simple\n"

    async def test_a_failed_sync_hands_the_tail_of_uvs_output_to_the_model(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, workspace: Path
    ) -> None:
        install_fake_uv(monkeypatch, tmp_path, 'echo "Resolving..."; echo "No solution found" >&2; exit 2')
        log = tmp_path / "app.log"

        with pytest.raises(AppLaunchFailed, match=r"exited with 2\):\nResolving...\nNo solution found$"):
            await sync_project_environment(workspace, log)
        # 全文进应用日志，read_app_log 在那儿找得到。
        assert "No solution found" in log.read_text()

    async def test_a_sync_past_the_deadline_is_killed_and_reported(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, workspace: Path
    ) -> None:
        monkeypatch.setattr(project_env_mod, "SYNC_TIMEOUT_SECONDS", 0.2)
        pid_file = tmp_path / "uv.pid"
        install_fake_uv(monkeypatch, tmp_path, f'echo $$ > "{pid_file}"; sleep 30')

        with pytest.raises(AppLaunchFailed, match="did not finish within"):
            await sync_project_environment(workspace, tmp_path / "app.log")

        with pytest.raises(ProcessLookupError):
            os.kill(int(pid_file.read_text()), 0)

    async def test_a_missing_uv_is_reported_as_the_platforms_problem(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, workspace: Path
    ) -> None:
        """说清楚不是代码的问题，免得模型自己去装一个 uv。"""
        monkeypatch.setenv("PATH", str(tmp_path / "empty"))

        with pytest.raises(AppLaunchFailed, match="`uv` command is missing"):
            await sync_project_environment(workspace, tmp_path / "app.log")

    async def test_an_unwritable_log_does_not_block_the_launch(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, workspace: Path
    ) -> None:
        install_fake_uv(monkeypatch, tmp_path, "echo ok")

        await sync_project_environment(workspace, tmp_path / "missing-dir" / "app.log")
