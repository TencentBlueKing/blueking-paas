"""Vendored github/gitignore templates: merge, registry, and the update script."""

from __future__ import annotations

from pathlib import Path

import pytest

from app_spark_agent.git.ignores import (
    GITIGNORE_LANGUAGES,
    GitignoreLanguage,
    load_default_excludes,
)
from app_spark_agent.git.policy import get_default_excludes
from app_spark_agent.git.update_assets import download_templates, fetch_url, main


def test_the_registry_is_python_and_node():
    assert [(spec.language, spec.source) for spec in GITIGNORE_LANGUAGES] == [
        ("python", "Python.gitignore"),
        ("node", "Node.gitignore"),
    ]


def test_merge_keeps_later_platform_rules_after_the_templates(tmp_path: Path):
    (tmp_path / "Python.gitignore").write_text(".env\nlib/\n")

    lines = load_default_excludes(tmp_path, (GitignoreLanguage("python", "Python.gitignore"),))

    assert lines.index(".env") < lines.index("!.env")
    assert lines.index("lib/") < lines.index("!lib/")


def test_a_missing_template_tells_you_how_to_fetch_it(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="make update-gitignore-assets"):
        load_default_excludes(tmp_path, (GitignoreLanguage("python", "Python.gitignore"),))


def test_vendored_assets_cover_every_registered_source():
    """A checkout without a `make update-gitignore-assets` still has a complete exclude list."""
    lines = load_default_excludes()
    assert ".venv" in lines
    assert "node_modules/" in lines
    assert "*.tsbuildinfo" in lines
    assert ".nuxt" in lines


def test_get_default_excludes_is_cached():
    assert get_default_excludes() is get_default_excludes()
    assert get_default_excludes() == load_default_excludes()


def test_download_creates_nested_source_paths(tmp_path: Path):
    languages = (
        GitignoreLanguage("python", "Python.gitignore"),
        GitignoreLanguage("vue", "community/JavaScript/Vue.gitignore"),
    )
    fetched: list[str] = []

    def fetch(url: str) -> str:
        fetched.append(url)
        return f"# from {url}\nignored/\n"

    written = download_templates(tmp_path, languages, fetch=fetch)

    assert len(fetched) == 2
    assert {path.relative_to(tmp_path).as_posix() for path in written} == {
        "Python.gitignore",
        "community/JavaScript/Vue.gitignore",
    }
    assert (tmp_path / "community" / "JavaScript" / "Vue.gitignore").read_text(encoding="utf-8").startswith("# from ")


def test_download_refuses_an_empty_body(tmp_path: Path):
    with pytest.raises(RuntimeError, match="body was empty"):
        download_templates(
            tmp_path,
            (GitignoreLanguage("python", "Python.gitignore"),),
            fetch=lambda url: "\n",
        )


def test_fetch_url_refuses_non_https():
    with pytest.raises(ValueError, match="only https is allowed"):
        fetch_url("file:///etc/passwd")


def test_main_writes_into_an_explicit_dest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "app_spark_agent.git.update_assets.download_templates",
        lambda dest, **kwargs: [dest / "Python.gitignore"],
    )
    (tmp_path / "Python.gitignore").write_text("ok\n")

    assert main(["--dest", str(tmp_path)]) == 0
