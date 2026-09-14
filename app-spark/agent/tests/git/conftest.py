"""Real git, real repositories, real processes.

A bare repository on the filesystem stands in for the Git host wherever the test is about git's
own behaviour rather than about the network: the interesting cases (a diverged push, an empty
remote, a rename) reproduce exactly, and no fixture has to decide what git "would have" printed.
Authentication and transport are the part a local remote cannot fake; those live in
``tests/live_forgejo``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from app_spark_agent.git import GitIdentity, GitRunner, GitWorkspace, RemoteConfig

IDENTITY = GitIdentity(name="App-Spark Test", email="app-spark-test@localhost.invalid")
BRANCH = "main"
GIT = shutil.which("git") or "git"

# A neutral environment for the raw git calls these tests make to check up on the component.
# Developers' own `~/.gitconfig` files really do carry `commit.gpgsign = true` and credential
# helpers, and a test that inherited them would fail for reasons that have nothing to do with the
# code under test. `GitRunner` neutralises the same settings for the same reason.
PLAIN_GIT_ENV = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_SYSTEM": "/dev/null",
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_AUTHOR_NAME": "Other Writer",
    "GIT_AUTHOR_EMAIL": "other@localhost.invalid",
    "GIT_COMMITTER_NAME": "Other Writer",
    "GIT_COMMITTER_EMAIL": "other@localhost.invalid",
    "LC_ALL": "C",
}


def plain_git(*args: str, cwd: Path) -> str:
    """Run git directly, outside the component, to check what it actually stored.

    :param args: Arguments after the binary.
    :param cwd: Directory to run in.
    :return: Standard output.
    """
    return subprocess.run(
        [GIT, *args],
        cwd=cwd,
        env={**os.environ, **PLAIN_GIT_ENV},
        check=True,
        capture_output=True,
        text=True,
    ).stdout


@pytest.fixture(scope="session", autouse=True)
def require_git() -> str:
    """Fail the whole module rather than skip: these tests are the reason git is in the image."""
    git = shutil.which("git")
    if git is None:
        pytest.fail("git must be installed to run the Git workspace tests")
    return git


@pytest.fixture
def bare_remote(tmp_path: Path) -> Path:
    """An empty bare repository standing in for the Project's remote."""
    remote = tmp_path / "remote.git"
    plain_git("init", "--bare", "--initial-branch", BRANCH, str(remote), cwd=tmp_path)
    return remote


@pytest.fixture
def workspace_dir(tmp_path: Path) -> Path:
    """An existing, empty workspace directory."""
    path = tmp_path / "workspace"
    path.mkdir()
    return path


def make_workspace(path: Path, remote: Path | None, *, branch: str = BRANCH) -> GitWorkspace:
    """Build a workspace pointed at ``remote``, or a local-only one when it is ``None``."""
    remote_config = (
        RemoteConfig(url=str(remote), branch=branch, username="tester", token="unused-locally")
        if remote is not None
        else None
    )
    return GitWorkspace(
        path=path,
        runner=GitRunner(workspace=path, identity=IDENTITY, remote=remote_config, timeout_seconds=60.0),
    )


@pytest.fixture
def workspace(workspace_dir: Path, bare_remote: Path) -> GitWorkspace:
    """A workspace attached to an empty bare remote, not yet initialised."""
    return make_workspace(workspace_dir, bare_remote)


def clone_to(remote: Path, target: Path, *, branch: str = BRANCH) -> Path:
    """Clone ``remote`` into ``target`` with plain git, to read back what a push really stored."""
    plain_git("clone", "--branch", branch, str(remote), str(target), cwd=target.parent)
    return target
