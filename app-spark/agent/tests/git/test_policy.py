"""The file policy on its own: ceilings, the messages they produce, and the exclude document."""

from __future__ import annotations

from pathlib import Path

import pytest

from app_spark_agent.git import GitPolicyError, WorkspaceFile, WorkspacePolicy
from app_spark_agent.git.policy import measure


class TestCeilings:
    def test_content_within_both_ceilings_passes(self):
        WorkspacePolicy(max_file_bytes=100, max_total_bytes=200).check(
            [WorkspaceFile("a.txt", 60), WorkspaceFile("b.txt", 60)]
        )

    def test_a_single_oversized_file_is_refused(self):
        policy = WorkspacePolicy(max_file_bytes=100, max_total_bytes=10_000)

        with pytest.raises(GitPolicyError) as exc:
            policy.check([WorkspaceFile("ok.txt", 10), WorkspaceFile("model.bin", 5000)])

        assert exc.value.paths == ("model.bin",)

    def test_the_total_is_refused_even_when_every_file_is_small(self):
        policy = WorkspacePolicy(max_file_bytes=1000, max_total_bytes=1000)

        with pytest.raises(GitPolicyError) as exc:
            policy.check([WorkspaceFile(f"chunk-{index}.txt", 400) for index in range(5)])

        assert len(exc.value.paths) == 5

    def test_the_message_names_the_worst_offenders_largest_first(self):
        policy = WorkspacePolicy(max_file_bytes=10, max_total_bytes=10_000)

        with pytest.raises(GitPolicyError) as exc:
            policy.check([WorkspaceFile("small.bin", 20), WorkspaceFile("big.bin", 900)])

        assert exc.value.paths == ("big.bin", "small.bin")
        assert str(exc.value).index("big.bin") < str(exc.value).index("small.bin")


class TestExcludeDocument:
    def test_it_lists_the_rebuildable_directories(self):
        document = WorkspacePolicy().exclude_document()
        assert ".venv/" in document
        assert "node_modules/" in document

    def test_it_says_it_is_generated(self):
        """Anyone who finds this file has to know that editing it achieves nothing."""
        assert "App-Spark" in WorkspacePolicy().exclude_document().splitlines()[0]


class TestMeasure:
    def test_a_symlink_is_measured_as_the_link_not_its_target(self, tmp_path: Path):
        (tmp_path / "real.bin").write_bytes(b"x" * 5000)
        (tmp_path / "link.bin").symlink_to("real.bin")

        sizes = {item.path: item.size for item in measure(tmp_path, ["real.bin", "link.bin"])}

        assert sizes["real.bin"] == 5000
        assert sizes["link.bin"] < 100

    def test_a_path_git_reported_but_disk_no_longer_has_costs_nothing(self, tmp_path: Path):
        assert measure(tmp_path, ["deleted.txt"]) == [WorkspaceFile("deleted.txt", 0)]
