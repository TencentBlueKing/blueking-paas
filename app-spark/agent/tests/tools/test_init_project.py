"""The model's init_project tool: the name it accepts, the files it writes, what it reports back."""

import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from app_spark_agent.app_supervisor import uv_environ
from app_spark_agent.tools.init_project import (
    EXISTS_DETAIL,
    REPLACED_LOCK_DETAIL,
    InitProjectResult,
    ProjectInitializer,
    build_init_project_tool,
)

TEMPLATE = Path(__file__).parents[2] / "app-template"


def root_package(lock: Path) -> dict[str, object]:
    """Return the lock's entry for the project itself, the one uv records as virtual."""
    packages = tomllib.loads(lock.read_text())["package"]
    (root,) = [package for package in packages if package["source"] == {"virtual": "."}]
    return root


class TestNormalizeName:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("todo-board", "todo-board"),
            ("Todo Board", "todo-board"),
            ("todo_board", "todo-board"),
            ("  Todo.._Board  ", "todo-board"),
            ("-todo-", "todo"),
            ("app2", "app2"),
        ],
    )
    def test_returns_the_form_uv_records(self, raw: str, expected: str) -> None:
        assert ProjectInitializer.normalize_name(raw) == expected

    @pytest.mark.parametrize("raw", ["", "  ", "---", "待办看板", "todo!", "a" * 65])
    def test_refuses_what_cannot_become_a_project_name(self, raw: str) -> None:
        assert ProjectInitializer.normalize_name(raw) is None


class TestInit:
    def test_a_new_workspace_gets_the_template_under_the_normalized_name(self, tmp_path: Path) -> None:
        result = ProjectInitializer(tmp_path).init("Todo Board")

        assert result == InitProjectResult(status="created", name="todo-board")
        assert tomllib.loads((tmp_path / "pyproject.toml").read_text())["project"]["name"] == "todo-board"
        assert root_package(tmp_path / "uv.lock")["name"] == "todo-board"

    def test_nothing_but_the_name_differs_from_the_template(self, tmp_path: Path) -> None:
        """锁文件其余部分逐字不变，uv 才认它没过期，新项目首次启动才能只走预热好的缓存。"""
        ProjectInitializer(tmp_path).init("todo-board")

        for name in ("pyproject.toml", "uv.lock"):
            written = (tmp_path / name).read_text().splitlines()
            template = (TEMPLATE / name).read_text().splitlines()
            changed = [(old, new) for old, new in zip(template, written, strict=True) if old != new]
            assert changed == [('name = "app"', 'name = "todo-board"')]

    def test_uv_still_considers_the_renamed_lock_fresh(self, tmp_path: Path) -> None:
        """改了名的锁文件不需要联网重锁：空缓存、断网下 uv 也认它与 pyproject.toml 一致。"""
        uv = shutil.which("uv")
        if uv is None:
            pytest.skip("needs the uv command")
        ProjectInitializer(tmp_path).init("todo-board")

        result = subprocess.run(
            [uv, "lock", "--check", "--offline"],
            cwd=tmp_path,
            env={
                **uv_environ(os.environ),
                "UV_CACHE_DIR": str(tmp_path / "empty-cache"),
                "UV_PYTHON": sys.executable,
            },
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr

    def test_an_existing_pyproject_leaves_the_workspace_alone(self, tmp_path: Path) -> None:
        """补一份模板锁只会造出一对互不匹配的文件；缺的锁由 uv add / uv sync 就地补。"""
        (tmp_path / "pyproject.toml").write_text("# the user's own\n")

        result = ProjectInitializer(tmp_path).init("todo-board")

        assert result == InitProjectResult(status="exists", detail=EXISTS_DETAIL)
        assert sorted(path.name for path in tmp_path.iterdir()) == ["pyproject.toml"]
        assert (tmp_path / "pyproject.toml").read_text() == "# the user's own\n"

    def test_a_lone_uv_lock_is_replaced_by_the_template(self, tmp_path: Path) -> None:
        """只剩 uv.lock 时 launch 让模型调 init_project；这里再拒绝就成了死循环。

        uv add 在没有 pyproject.toml 的目录里直接失败，提示词又禁止手写这两个文件，所以
        init_project 是唯一能走通的一步。两个文件都按模板重写，仍是配套的一对。
        """
        (tmp_path / "uv.lock").write_text("# left behind\n")

        result = ProjectInitializer(tmp_path).init("todo-board")

        assert result == InitProjectResult(status="created", name="todo-board", detail=REPLACED_LOCK_DETAIL)
        assert sorted(path.name for path in tmp_path.iterdir()) == ["pyproject.toml", "uv.lock"]
        assert root_package(tmp_path / "uv.lock")["name"] == "todo-board"

    def test_an_invalid_name_is_handed_back_instead_of_raised(self, tmp_path: Path) -> None:
        """Raising out of a tool ends the turn; the model can simply pick another name."""
        result = ProjectInitializer(tmp_path).init("待办看板")

        assert result.status == "invalid_name"
        assert "for example `todo-board`" in result.detail
        assert list(tmp_path.iterdir()) == []


def test_the_tool_creates_the_project_once(tmp_path: Path) -> None:
    init_project = build_init_project_tool(tmp_path)

    assert init_project("Todo Board") == InitProjectResult(status="created", name="todo-board")
    before = (tmp_path / "pyproject.toml").read_bytes()

    assert init_project("another-name") == InitProjectResult(status="exists", detail=EXISTS_DETAIL)
    assert (tmp_path / "pyproject.toml").read_bytes() == before
