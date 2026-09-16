"""Vendored github/gitignore templates that feed :class:`WorkspacePolicy`.

The platform default excludes used to be a short hand-maintained list. Language templates
from `github/gitignore`_ cover the same rebuildable paths more completely, and adding a
language is a new :class:`GitignoreLanguage` row plus ``make update-gitignore-assets``.

``node`` is GitHub's ``Node.gitignore``. It is what JavaScript, TypeScript and Vue actually
use: there is no TypeScript template, and ``community/JavaScript/Vue.gitignore`` only adds
``test/``, which would drop project tests on restore.

Runtime never fetches the network. The files under :func:`assets_root` are the source of
truth; the make target is how they get there.

.. _github/gitignore: https://github.com/github/gitignore
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

# Branch-pinned so a `make update-gitignore-assets` is reproducible until we choose to move.
GITIGNORE_RAW_BASE = "https://raw.githubusercontent.com/github/gitignore/refs/heads/main/"


@dataclass(frozen=True)
class GitignoreLanguage:
    """One language whose github/gitignore file we vendor.

    :param language: Stable id used in logs and the generated exclude header.
    :param source: Path inside the github/gitignore repository, e.g. ``Python.gitignore``
        or ``community/JavaScript/Vue.gitignore``. Local files keep this relative path
        under ``git/assets/``.
    """

    language: str
    source: str

    def raw_url(self) -> str:
        return f"{GITIGNORE_RAW_BASE}{self.source}"


# Add a language by appending a row. Re-run ``make update-gitignore-assets`` afterwards.
GITIGNORE_LANGUAGES: tuple[GitignoreLanguage, ...] = (
    GitignoreLanguage("python", "Python.gitignore"),
    GitignoreLanguage("node", "Node.gitignore"),
)

# OS / editor noise the language templates do not cover. Same intent as the old hand list.
PLATFORM_EXTRAS: tuple[str, ...] = (
    ".DS_Store",
    "Thumbs.db",
)

# Templates treat env files as secrets. This platform's restore contract keeps them: a
# missing ``.env`` after cold start is worse than storing it. ``lib/`` is a setuptools
# artifact in GitHub's Python template, but a project may keep source there.
PLATFORM_KEEP: tuple[str, ...] = (
    "!.env",
    "!.python-version",
    "!lib/",
)


def assets_root() -> Path:
    """Filesystem path of ``git/assets``. Writable in an editable/source install."""
    return Path(str(files("app_spark_agent.git").joinpath("assets")))


def load_default_excludes(
    root: Path | None = None,
    languages: tuple[GitignoreLanguage, ...] = GITIGNORE_LANGUAGES,
) -> tuple[str, ...]:
    """Merge vendored templates into gitignore lines for ``.git/info/exclude``.

    ``root`` is the assets directory; omitted, it is the package's vendored copy.
    """
    assets = root if root is not None else assets_root()
    lines: list[str] = []
    for spec in languages:
        lines.append(f"# --- {spec.language}: {spec.source} ---")
        lines.extend(_read_template(assets, spec.source).splitlines())
        lines.append("")
    if PLATFORM_EXTRAS:
        lines.append("# --- platform extras ---")
        lines.extend(PLATFORM_EXTRAS)
        lines.append("")
    if PLATFORM_KEEP:
        lines.append("# --- platform keep (restore contract) ---")
        lines.extend(PLATFORM_KEEP)
        lines.append("")
    while lines and lines[-1] == "":
        lines.pop()
    return tuple(lines)


def _read_template(root: Path, source: str) -> str:
    path = root.joinpath(*Path(source).parts)
    if not path.is_file():
        raise FileNotFoundError(
            f"gitignore template {source} is missing from {root}; "
            "run `make update-gitignore-assets` from the agent directory"
        )
    return path.read_text(encoding="utf-8")
