"""Behaviour of :class:`~app_spark_agent.git.workspace.GitWorkspace` against real repositories."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app_spark_agent.git import (
    GitCommandError,
    GitDivergedError,
    GitPolicyError,
    GitTimeoutError,
    GitWorkspace,
    GitWorkspaceConflictError,
    WorkspacePolicy,
)
from tests.git.conftest import BRANCH, clone_to, make_workspace, plain_git


def write(workspace: GitWorkspace, name: str, content: str = "hello\n") -> Path:
    path = workspace.path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


class TestEnsureReady:
    def test_empty_workspace_and_empty_remote_initialises(self, workspace: GitWorkspace):
        assert workspace.ensure_ready() == "initialised"
        assert workspace.initialised
        assert workspace.head() is None

    def test_second_call_reuses_the_repository(self, workspace: GitWorkspace):
        workspace.ensure_ready()
        write(workspace, "keep.txt")
        first = workspace.commit("first")

        assert workspace.ensure_ready() == "reused"
        assert workspace.head() == first

    def test_empty_workspace_takes_the_remote_history(self, workspace: GitWorkspace, tmp_path: Path):
        workspace.ensure_ready()
        write(workspace, "index.html", "<h1>hi</h1>\n")
        pushed = workspace.commit("first")
        workspace.push()

        fresh = make_workspace(tmp_path / "fresh", Path(workspace.runner.remote.url))
        fresh.path.mkdir()

        assert fresh.ensure_ready() == "cloned"
        assert fresh.head() == pushed
        assert (fresh.path / "index.html").read_text() == "<h1>hi</h1>\n"

    def test_existing_files_and_existing_history_is_refused(self, workspace: GitWorkspace, tmp_path: Path):
        """Neither side may be silently dropped, so this one is the caller's decision."""
        workspace.ensure_ready()
        write(workspace, "remote-only.txt")
        workspace.commit("first")
        workspace.push()

        occupied = make_workspace(tmp_path / "occupied", Path(workspace.runner.remote.url))
        occupied.path.mkdir()
        (occupied.path / "local-only.txt").write_text("work nobody pushed\n")

        with pytest.raises(GitWorkspaceConflictError, match=re.escape("local-only.txt")):
            occupied.ensure_ready()

    def test_ignored_leftovers_do_not_block_taking_the_history(self, workspace: GitWorkspace, tmp_path: Path):
        """A recycled sandbox keeps its `.venv`; that must not read as "the workspace is in use"."""
        workspace.ensure_ready()
        write(workspace, "app.py", "print('hi')\n")
        workspace.commit("first")
        workspace.push()

        recycled = make_workspace(tmp_path / "recycled", Path(workspace.runner.remote.url))
        recycled.path.mkdir()
        (recycled.path / ".venv").mkdir()
        (recycled.path / ".venv" / "pyvenv.cfg").write_text("home = /usr\n")

        assert recycled.ensure_ready() == "cloned"
        assert (recycled.path / "app.py").exists()
        assert (recycled.path / ".venv" / "pyvenv.cfg").exists()


class TestCommit:
    def test_records_additions(self, workspace: GitWorkspace):
        workspace.ensure_ready()
        write(workspace, "a.txt")
        write(workspace, "nested/b.txt")

        sha = workspace.commit("add two files")

        assert sha is not None
        assert set(_tracked(workspace)) == {"a.txt", "nested/b.txt"}

    def test_records_modifications_deletions_and_renames(self, workspace: GitWorkspace):
        workspace.ensure_ready()
        write(workspace, "keep.txt", "v1\n")
        write(workspace, "drop.txt")
        write(workspace, "old-name.txt", "moved content\n")
        workspace.commit("first")

        write(workspace, "keep.txt", "v2\n")
        (workspace.path / "drop.txt").unlink()
        (workspace.path / "old-name.txt").rename(workspace.path / "new-name.txt")

        # Before staging, git has not yet paired the two halves of the rename, so it reports the
        # disappearance and the new file separately. That is the input `commit` has to handle.
        assert set(workspace.status().paths) == {"keep.txt", "drop.txt", "old-name.txt", "new-name.txt"}
        assert workspace.commit("second") is not None

        assert set(_tracked(workspace)) == {"keep.txt", "new-name.txt"}
        assert (workspace.path / "keep.txt").read_text() == "v2\n"
        # Git records renames as content and pairs them when a diff is read back.
        renames = plain_git("diff", "--name-status", "-M", "HEAD~1", "HEAD", cwd=workspace.path)
        assert "R" in renames
        assert "old-name.txt" in renames

    def test_a_staged_rename_is_reported_with_its_original_path(self, workspace: GitWorkspace):
        workspace.ensure_ready()
        write(workspace, "old-name.txt", "moved content\n")
        workspace.commit("first")
        (workspace.path / "old-name.txt").rename(workspace.path / "new-name.txt")
        workspace.runner.run("add", "--all", "--", ".")

        entry = next(item for item in workspace.status().entries if item.path == "new-name.txt")

        assert entry.index_status == "R"
        assert entry.renamed_from == "old-name.txt"

    def test_no_changes_makes_no_commit(self, workspace: GitWorkspace):
        workspace.ensure_ready()
        write(workspace, "a.txt")
        first = workspace.commit("first")

        assert workspace.commit("second") is None
        assert workspace.head() == first

    def test_ignored_files_are_not_committed(self, workspace: GitWorkspace):
        workspace.ensure_ready()
        write(workspace, "app.py")
        write(workspace, "node_modules/left-pad/index.js")
        write(workspace, "__pycache__/app.cpython-314.pyc")
        write(workspace, ".gitignore", "secret-notes.txt\n")
        write(workspace, "secret-notes.txt")

        workspace.commit("first")

        assert set(_tracked(workspace)) == {"app.py", ".gitignore"}

    def test_dotfiles_are_committed(self, workspace: GitWorkspace):
        """Hidden files are project files; a restore that dropped them would be the worse bug."""
        workspace.ensure_ready()
        write(workspace, ".env", "APP_DEBUG=1\n")
        write(workspace, ".python-version", "3.14\n")

        workspace.commit("first")

        assert set(_tracked(workspace)) == {".env", ".python-version"}

    def test_symlinks_are_committed_as_links(self, workspace: GitWorkspace):
        workspace.ensure_ready()
        write(workspace, "real.txt", "content\n")
        (workspace.path / "link.txt").symlink_to("real.txt")

        workspace.commit("first")

        mode = plain_git("ls-files", "--stage", "link.txt", cwd=workspace.path)
        assert mode.startswith("120000"), mode

    def test_trailers_tie_a_commit_to_its_run(self, workspace: GitWorkspace):
        workspace.ensure_ready()
        write(workspace, "a.txt")

        workspace.commit("turn 1", trailers={"Run-Id": "run-7", "Conversation-Id": "conv-3"})

        message = plain_git("log", "-1", "--format=%B", cwd=workspace.path)
        assert "Run-Id: run-7" in message
        assert "Conversation-Id: conv-3" in message

    def test_commit_uses_the_configured_robot_identity(self, workspace: GitWorkspace):
        workspace.ensure_ready()
        write(workspace, "a.txt")
        workspace.commit("first")

        author = plain_git("log", "-1", "--format=%an <%ae> | %cn <%ce>", cwd=workspace.path).strip()
        assert author == (
            "App-Spark Test <app-spark-test@localhost.invalid> | App-Spark Test <app-spark-test@localhost.invalid>"
        )


class TestPolicy:
    def test_a_file_over_the_ceiling_is_refused_by_name(self, workspace: GitWorkspace):
        workspace.policy = WorkspacePolicy(max_file_bytes=1024, max_total_bytes=1024 * 1024)
        workspace.ensure_ready()
        write(workspace, "small.txt")
        write(workspace, "huge.bin", "x" * 4096)

        with pytest.raises(GitPolicyError) as exc:
            workspace.commit("first")

        assert exc.value.paths == ("huge.bin",)
        assert "huge.bin" in str(exc.value)
        # Refused before staging: the index is untouched and there is still nothing committed.
        assert workspace.head() is None

    def test_the_total_ceiling_names_the_largest_paths(self, workspace: GitWorkspace):
        workspace.policy = WorkspacePolicy(max_file_bytes=1024 * 1024, max_total_bytes=4096)
        workspace.ensure_ready()
        write(workspace, "a.bin", "x" * 3000)
        write(workspace, "b.bin", "x" * 3000)

        with pytest.raises(GitPolicyError, match="over the"):
            workspace.commit("first")

    def test_excluded_directories_do_not_count_towards_the_ceiling(self, workspace: GitWorkspace):
        workspace.policy = WorkspacePolicy(max_file_bytes=1024 * 1024, max_total_bytes=4096)
        workspace.ensure_ready()
        write(workspace, "app.py")
        write(workspace, "node_modules/big/index.js", "x" * 100_000)

        assert workspace.commit("first") is not None


class TestPushAndRestore:
    def test_push_makes_the_content_readable_from_a_fresh_clone(self, workspace: GitWorkspace, tmp_path: Path):
        workspace.ensure_ready()
        write(workspace, "index.html", "<h1>generated</h1>\n")
        sha = workspace.commit("first")

        assert workspace.push() == sha

        read_back = clone_to(Path(workspace.runner.remote.url), tmp_path / "read-back")
        assert (read_back / "index.html").read_text() == "<h1>generated</h1>\n"

    def test_push_reports_divergence_instead_of_forcing(self, workspace: GitWorkspace, tmp_path: Path):
        workspace.ensure_ready()
        write(workspace, "a.txt")
        workspace.commit("first")
        workspace.push()

        # A second writer moves the branch on, the way a replacement Runtime would.
        other = clone_to(Path(workspace.runner.remote.url), tmp_path / "other")
        (other / "b.txt").write_text("from the other writer\n")
        plain_git("add", "-A", cwd=other)
        plain_git("commit", "-m", "other", cwd=other)
        plain_git("push", "origin", BRANCH, cwd=other)

        write(workspace, "c.txt")
        workspace.commit("second")

        with pytest.raises(GitDivergedError):
            workspace.push()

        # And the other writer's commit is still the tip: nothing was overwritten.
        after = clone_to(Path(workspace.runner.remote.url), tmp_path / "after")
        assert (after / "b.txt").exists()
        assert not (after / "c.txt").exists()

    def test_unpushed_commits_are_counted(self, workspace: GitWorkspace):
        workspace.ensure_ready()
        write(workspace, "a.txt")
        workspace.commit("first")

        assert workspace.unpushed_commits() == 1
        workspace.push()
        assert workspace.unpushed_commits() == 0

    def test_restore_reproduces_an_older_commit(self, workspace: GitWorkspace):
        workspace.ensure_ready()
        write(workspace, "page.html", "v1\n")
        first = workspace.commit("first")
        write(workspace, "page.html", "v2\n")
        write(workspace, "extra.txt")
        workspace.commit("second")

        workspace.restore(first)

        assert workspace.head() == first
        assert (workspace.path / "page.html").read_text() == "v1\n"
        assert not (workspace.path / "extra.txt").exists()

    def test_restore_discards_local_mess_but_keeps_ignored_files(self, workspace: GitWorkspace):
        workspace.ensure_ready()
        write(workspace, "page.html", "v1\n")
        first = workspace.commit("first")

        write(workspace, "page.html", "half-finished\n")
        write(workspace, "scratch.txt")
        write(workspace, ".venv/pyvenv.cfg", "home = /usr\n")

        workspace.restore(first)

        assert (workspace.path / "page.html").read_text() == "v1\n"
        assert not (workspace.path / "scratch.txt").exists()
        assert (workspace.path / ".venv" / "pyvenv.cfg").exists()

    def test_restore_to_an_unknown_commit_fails_loudly(self, workspace: GitWorkspace):
        workspace.ensure_ready()
        write(workspace, "a.txt")
        workspace.commit("first")

        with pytest.raises(GitCommandError, match="cannot be restored"):
            workspace.restore("0" * 40)


class TestFailureModes:
    def test_a_missing_remote_is_reported_as_unreachable(self, workspace_dir: Path, tmp_path: Path):
        workspace = make_workspace(workspace_dir, tmp_path / "not-a-repository")
        # A local path that is not a repository is git's version of "the remote is not there".
        with pytest.raises(GitCommandError):
            workspace.remote_branch_head()

    def test_a_command_that_outlives_its_timeout_is_killed(self, workspace: GitWorkspace):
        workspace.ensure_ready()
        workspace.runner.timeout_seconds = 0.001

        with pytest.raises(GitTimeoutError):
            # `git help --all` is slow enough to lose a millisecond race, and changes nothing.
            workspace.runner.run("help", "--all")


def _tracked(workspace: GitWorkspace) -> list[str]:
    """Every path the repository has committed."""
    return plain_git("ls-tree", "-r", "--name-only", "HEAD", cwd=workspace.path).split()
